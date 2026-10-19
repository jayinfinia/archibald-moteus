#!/usr/bin/env python3
"""Rebuild the actual KiCad netlist/ERC, check connectivity and test the checks.

Python 3 standard library and KiCad CLI required. Does not power hardware or
change the schematic. Exit 1: regression; exit 2 with --strict-release: blocked.
"""
from pathlib import Path
import argparse, collections, copy, datetime, hashlib, json, os, re
import shutil, subprocess, sys, xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
RESULTS = HERE / 'results'
BASE = HERE / 'baseline'

def parse_sexpr(path):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', path.read_text())
    stack = []; result = None
    for t in tokens:
        if t == '(':
            n = []
            if stack: stack[-1].append(n)
            stack.append(n)
        elif t == ')':
            if not stack: raise ValueError('Unbalanced schematic')
            result = stack.pop()
        else:
            stack[-1].append(json.loads(t) if t.startswith('"') else t)
    if stack or not isinstance(result, list): raise ValueError('Incomplete schematic')
    return result

def children(n, tag): return [x for x in n if isinstance(x, list) and x and x[0] == tag]
def child(n, tag): return next(iter(children(n, tag)), None)
def props(n): return {x[1]:x[2] for x in children(n, 'property')}

class Circuit:
    def __init__(self, path):
        self.xml = ET.parse(path).getroot()
        self.nets = [set((n.get('ref'), n.get('pin')) for n in net.findall('node'))
                     for net in self.xml.findall('./nets/net')]
        self.components = self.xml.findall('./components/comp')
        self.byref = {c.get('ref'):c for c in self.components}
        self.pages = [(int(s.get('number')), s.get('name'), s.findtext('./title_block/source'))
                      for s in self.xml.findall('./design/sheet')]
    def net(self, pin):
        hits = [n for n in self.nets if pin in n]
        if len(hits) != 1: raise AssertionError(f'{pin}: expected exactly one net, got {len(hits)}')
        return hits[0]
    def joined(self, *pins): return set(pins) <= self.net(pins[0])
    def exact(self, *pins): return set(pins) == self.net(pins[0])
    def pins(self, ref): return {p for n in self.nets for r,p in n if r == ref}
    def value(self, ref): return self.byref[ref].findtext('value')
    def dnp(self, ref): return self.byref[ref].find("property[@name='dnp']") is not None

CHECKS = []
def check(label):
    def deco(f): CHECKS.append((label,f)); return f
    return deco

EXPECTED_PAGES = [(1,'/','moteus_c1.kicad_sch'), (2,'/Power Input/','power_input.kicad_sch'),
 (3,'/stm32g4/','stm32g4.kicad_sch'), (4,'/Gate Driver/','gate_driver.kicad_sch'),
 (5,'/H Bridge A/','h_bridge.kicad_sch'), (6,'/H Bridge B/','h_bridge.kicad_sch'),
 (7,'/H Bridge C/','h_bridge.kicad_sch'), (8,'/Current Sense/','current_sense.kicad_sch'),
 (9,'/CAN/','can.kicad_sch'), (10,'/VT Sense/','vt_sense.kicad_sch'),
 (11,'/aux2/','aux2.kicad_sch'), (12,'/aux1/','aux1.kicad_sch'),
 (13,'/LED Sense/','led_sense.kicad_sch'), (14,'/Bulk Capacitance/','bulk_capacitance.kicad_sch')]

@check('H01 All 14 original C1 page instances are present')
def hierarchy(c): return sorted(c.pages) == EXPECTED_PAGES

@check('H02 Every linked schematic exists inside this package')
def files(c):
    return all((PROJECT/f).is_file() and (PROJECT/f).resolve().parent == PROJECT for _,_,f in c.pages)

@check('H03 Parent sheet ports match child hierarchical labels')
def ports(c):
    root = parse_sexpr(PROJECT/'moteus_c1.kicad_sch')
    for s in children(root,'sheet'):
        sub = parse_sexpr(PROJECT/props(s)['Sheetfile'])
        if {x[1] for x in children(s,'pin')} != {x[1] for x in children(sub,'hierarchical_label')}:
            return False
    return True

@check('H04 Component references are unique across repeated sheets')
def references(c): return len(c.byref) == len(c.components)

@check('H05 All three motor phases retain their own power components')
def phases(c):
    return all(c.byref[r].find('sheetpath').get('names') == f'/H Bridge {phase}/'
               for phase,refs in [('A',['Q1','Q2','X1','R6']),('B',['Q3','Q4','X2','R9']),('C',['Q5','Q6','X3','R12'])]
               for r in refs)

@check('S01 MCU TX/clock connects to R26, with both original MCU pins')
def tx_host(c): return c.exact(('U3','16'),('U3','33'),('R26','1'))

@check('S02 R26 connects only to U7 data input on the transceiver side')
def tx_chip(c): return c.exact(('R26','2'),('U7','4'))

@check('S03 MCU RX connects to R27; U7 output is on its other side')
def rx(c): return c.exact(('U3','45'),('R27','1')) and c.exact(('U7','1'),('R27','2'))

@check('S04 Encoder RX+ is driven by Y, not Z')
def y(c): return c.exact(('U7','6'),('J2','3'))

@check('S05 Encoder RX- is driven by Z, not Y')
def z(c): return c.exact(('U7','7'),('J2','4'))

@check('S06 Encoder TX+ reaches A and the optional termination')
def a(c): return c.exact(('U7','9'),('J2','5'),('R36','1'))

@check('S07 Encoder TX- reaches B and the optional termination')
def b(c): return c.exact(('U7','8'),('J2','6'),('R36','2'))

@check('S08 TX, RX and differential lines are not shorted together')
def signals_separate(c):
    pins=[('U7',p) for p in ['1','4','6','7','8','9']]
    return len({frozenset(c.net(p)) for p in pins}) == len(pins)

@check('P01 VCC and DE use the C1 3.3 V regulator output')
def supply(c): return c.joined(('U2','5'),('U7','10'),('U7','3'),('C50','1'))

@check('P02 Active-low RE, ground and exposed pad are grounded')
def ground(c): return c.joined(('U2','2'),('U7','2'),('U7','5'),('U7','11'),('C50','2'))

@check('P03 Ribbon pin 1 receives 5 V and pins 2/8 are ground')
def ribbon_power(c): return c.joined(('U1','4'),('J2','1')) and c.joined(('U2','2'),('J2','2'),('J2','8'),('J3','2'))

@check('P04 Battery positive connects only to encoder battery input')
def battery(c): return c.exact(('J2','7'),('J3','1'))

@check('P05 5 V, 3.3 V, battery positive and ground are separate nets')
def rails(c): return len({frozenset(c.net(p)) for p in [('J2','1'),('U7','10'),('J3','1'),('U7','5')]}) == 4

@check('P06 No communication signal is shorted directly to a power rail')
def no_signal_power_short(c):
    power=[('J2','1'),('U7','10'),('J3','1'),('U7','5')]
    return all(not any(p in c.net(('U7',s)) for p in power) for s in ['1','4','6','7','8','9'])

@check('C01 Transceiver has the correct part and exactly pins 1-11')
def chip(c): return c.value('U7') == 'THVD2442DRCR' and c.pins('U7') == {str(i) for i in range(1,12)}

@check('C02 Ribbon has all eight distinct numbered electrical pins')
def ribbon(c): return c.value('J2') == '0512810898' and c.pins('J2') == {str(i) for i in range(1,9)}

@check('C03 Local 100 nF bypass is connected across U7 supply')
def bypass(c): return c.value('C50') == '100nF' and c.joined(('C50','1'),('U7','10')) and c.joined(('C50','2'),('U7','5'))

@check('C04 Original 1 uF rail capacitors are retained')
def bulk(c):
    return all(c.value(r)=='1uF' and c.joined((r,'1'),p) and c.joined((r,'2'),('U7','5'))
               for r,p in [('C31',('J2','1')),('C32',('U7','10'))])

@check('C05 Both processor series resistors retain 100-ohm values')
def series(c): return c.value('R26')=='100' and c.value('R27')=='100'

@check('C06 Receive termination is 120 ohms and explicitly unpopulated')
def termination(c): return c.value('R36')=='120 DNP' and c.dnp('R36')

@check('C07 Old AUX2 connectors and switched I2C pullup are removed')
def retired(c): return not ({'AUX2','AUX2H1','R22','R23','R24','R25','D11','D12','C33','C34','C35','C36'} & set(c.byref))

@check('R01 Connectivity outside the encoder sheet matches stock C1')
def regression(c):
    base=Circuit(BASE/'original-netlist.xml')
    def external(x):return {r for r,v in x.byref.items() if v.find('sheetpath').get('names')!='/aux2/'}
    refs=external(base)
    if refs != external(c): return False
    def groups(x):return {frozenset((r,p) for r,p in n if r in refs) for n in x.nets}-{frozenset()}
    return groups(base)==groups(c)

@check('R02 Original non-encoder component values and footprints retained')
def values(c):
    base=Circuit(BASE/'original-netlist.xml')
    return all(c.byref[r].findtext('value')==v.findtext('value') and c.byref[r].findtext('footprint')==v.findtext('footprint')
               for r,v in base.byref.items() if v.find('sheetpath').get('names')!='/aux2/')

@check('R03 All other original child schematic files are byte-identical')
def hashes(c):
    original=json.loads((BASE/'original-file-hashes.json').read_text())
    return all(hashlib.sha256((PROJECT/n).read_bytes()).hexdigest()==digest
               for n,digest in original.items() if n not in ['aux2.kicad_sch','moteus_c1.kicad_sch'])

def reviewed_footprint():
    return parse_sexpr(PROJECT/'Encoder.pretty/TI_DRC0010J.kicad_mod')

@check('F01 U7 footprint assignment and manufacturer peripheral land geometry')
def package_lands(c):
    if c.byref['U7'].findtext('footprint') != 'Encoder:TI_DRC0010J': return False
    pads=children(reviewed_footprint(),'pad')
    electrical=[p for p in pads if p[1] and p[1]!='11']
    expected={str(i):((-1.4,(i-3)*.5) if i<=5 else (1.4,(8-i)*.5)) for i in range(1,11)}
    return len(electrical)==10 and all(
        p[1] in expected and tuple(map(float,child(p,'at')[1:3]))==expected[p[1]]
        and tuple(map(float,child(p,'size')[1:3]))==(.6,.24)
        and set(child(p,'layers')[1:])=={'F.Cu','F.Paste','F.Mask'} for p in electrical)

@check('F02 U7 exposed-pad geometry, grounding and segmented paste')
def package_ep(c):
    pads=children(reviewed_footprint(),'pad')
    def shape(p):return tuple(map(float,child(p,'at')[1:3]+child(p,'size')[1:3]))
    ep={shape(p) for p in pads if p[1]=='11'}
    expected={(0.,0.,1.65,2.4)}|{(x,y,.25,.5) for x in [-.25,.25] for y in [-1.45,1.45]}
    paste={shape(p) for p in pads if p[1]=='' and child(p,'layers')[1:]==['F.Paste']}
    stencil={(0.,y,1.5,1.06) for y in [-.63,.63]}|{(x,y,.25,.34) for x in [-.25,.25] for y in [-1.53,1.53]}
    return ep==expected and paste==stencil and c.joined(('U7','11'),('U2','2'))

@check('P01 Power-budget topology: encoder and 3.3 V LDO share 5 V buck')
def budget_topology(c):
    return (c.value('U1')=='MAX15062BATA+T' and c.value('U2')=='TLV70233PDBVR'
        and c.joined(('J2','1'),('U2','1'),('L1','1'))
        and c.joined(('U2','5'),('U7','10')))

@check('E01 Integrated encoder sheet has no ERC violations')
def encoder_erc(c):
    report=json.loads((RESULTS/'erc.json').read_text())
    ss=[s for s in report['sheets'] if s['path']=='/aux2/']
    return len(ss)==1 and not ss[0]['violations']

@check('E02 No unexplained new electrical ERC violations versus original C1')
def erc_regression(c):
    def counts(path):
        r=json.loads(path.read_text())
        return collections.Counter((s['path'],v['type'],v['severity'],v['description'],tuple(sorted(i['description'] for i in v['items'])))
          for s in r['sheets'] for v in s['violations'] if v['type'] not in ['footprint_link_issues','lib_symbol_mismatch'])
    additions=counts(RESULTS/'erc.json')-counts(BASE/'original-erc.json')
    # One explicit, reviewed delta: inherited MCU EPAD is typed unspecified.
    # The new /RE input shares that existing GND net. Do not hide it in KiCad
    # or broadly ignore pin-to-pin warnings. Accept only this exact pair and
    # only while both pins demonstrably share the regulator's ground net.
    known=('/stm32g4/','pin_to_pin','warning','Pins of type Unspecified and Input are connected',
      ('Symbol U3 Pin 49 [EPAD, Unspecified, Line]','Symbol U7 Pin 2 [~{RE}, Input, Line]'))
    if additions[known] == 1 and c.joined(('U3','49'),('U7','2'),('U2','2')):
        del additions[known]
    return not additions

def swap_pins(c,p,q):
    for net in c.nets:
        hasp,hasq=p in net,q in net
        net.discard(p); net.discard(q)
        if hasp:net.add(q)
        if hasq:net.add(p)

def mutate(c,name):
    if name=='reverse encoder input pair':swap_pins(c,('J2','3'),('J2','4')); return y
    if name=='reverse encoder output pair':swap_pins(c,('J2','5'),('J2','6')); return a
    if name=='swap chip UART input/output':swap_pins(c,('U7','1'),('U7','4')); return tx_chip
    if name=='short battery to 3.3 V':
        n=c.net(('J3','1'));other=c.net(('U7','10')); n.update(other);c.nets.remove(other);return rails
    if name=='disconnect local capacitor':c.net(('C50','1')).remove(('C50','1'));return bypass
    if name=='omit an H-bridge page':c.pages=[p for p in c.pages if p[0]!=6];return hierarchy
    if name=='populate DNP termination':
        e=c.byref['R36'];e.remove(e.find("property[@name='dnp']"));return termination
    if name=='drop ribbon pin 8':c.net(('J2','8')).remove(('J2','8'));return ribbon
    raise ValueError(name)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kicad-cli',default=os.environ.get('KICAD_CLI'))
    p.add_argument('--strict-release',action='store_true')
    args=p.parse_args()
    cli=args.kicad_cli or shutil.which('kicad-cli') or '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
    if not Path(cli).is_file():sys.exit('KiCad CLI not found. Supply --kicad-cli PATH.')
    RESULTS.mkdir(exist_ok=True)
    for filename in ['netlist.xml','erc.json']:
        (RESULTS/filename).unlink(missing_ok=True)
    log=[]
    for options in [['sch','export','netlist','--format','kicadxml','-o',str(RESULTS/'netlist.xml')],
                    ['sch','erc','--format','json','-o',str(RESULTS/'erc.json')]]:
        run=subprocess.run([cli,*options,str(PROJECT/'moteus_c1.kicad_sch')],text=True,capture_output=True)
        log.append(run.stdout+run.stderr)
        if run.returncode:sys.exit('KiCad export/check failed: '+log[-1])
    (RESULTS/'kicad-log.txt').write_text('\n'.join(log))
    c=Circuit(RESULTS/'netlist.xml'); result=[]
    for title,test in CHECKS:
        try: ok=bool(test(c)); detail='' if ok else 'Acceptance condition not met'
        except Exception as e:ok=False;detail=str(e)
        result.append(dict(test=title,status='PASS' if ok else 'FAIL',detail=detail))
    for name in ['reverse encoder input pair','reverse encoder output pair','swap chip UART input/output','short battery to 3.3 V',
                 'disconnect local capacitor','omit an H-bridge page','populate DNP termination','drop ribbon pin 8']:
        corrupt=copy.deepcopy(c)
        try:
            detector=mutate(corrupt,name)
            try: caught=not bool(detector(corrupt))
            except (AssertionError,KeyError):caught=True
            result.append(dict(test='M '+name,status='PASS' if caught else 'FAIL',detail='Injected defect detected' if caught else 'Defect missed'))
        except Exception as e:result.append(dict(test='M '+name,status='FAIL',detail='Mutation setup failed: '+str(e)))
    erc=json.loads((RESULTS/'erc.json').read_text());vv=[v for s in erc['sheets'] for v in s['violations']]
    gates=[('G01 Full-project ERC clearance',f"{len(vv)} remaining findings; see erc.json"),
      ('G02 Exact footprint and FPC contact-orientation review','U7 drawing-derived footprint assigned; J2/J3 geometry and cable orientation pending'),
      ('G03 Loaded/startup power and timing margins','Conditional loaded budget documented; maximum/startup, base-load, thermal and timing evidence pending'),
      ('G04 Complete modified C1 PCB and manufacturing checks','No integrated PCB layout; connector/CAN-pad changes pending'),
      ('G05 UART, BiSS, battery and motor bench tests','No assembled board or recorded bench results')]
    # These are release gates requiring engineering evidence, not inferred passes.
    for title,detail in gates:result.append(dict(test=title,status='BLOCKED',detail=detail))
    counts=collections.Counter(x['status'] for x in result)
    report={'timestamp':datetime.datetime.now().astimezone().isoformat(),'counts':dict(counts),
      'schematic_sha256':{f:hashlib.sha256((PROJECT/f).read_bytes()).hexdigest() for _,_,f in c.pages},'results':result}
    (RESULTS/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    lines=['# C1 encoder test results','',f"Run: {report['timestamp']}",'',
      f"**{counts['PASS']} passed; {counts['FAIL']} failed; {counts['BLOCKED']} release gates blocked.**",'',
      'These are structural schematic checks, not circuit simulation or evidence of working hardware. Fresh netlist and ERC generated from the packaged full C1 project.', '',
      '| Test | Result | Evidence / limitation |','|---|---|---|']
    lines += [f"| {r['test']} | {r['status']} | {r['detail'].replace('|','/')} |" for r in result]
    lines += ['', 'Default exit code tests regressions; use `--strict-release` to return nonzero while any release gate remains blocked.','',
      'The baseline is a frozen original C1 comparison, not proof of correctness. Review gates must be rerun/reassessed as the design evolves.']
    (PROJECT/'Test-Results.md').write_text('\n'.join(lines)+'\n')
    print(f"{counts['PASS']} passed; {counts['FAIL']} failed; {counts['BLOCKED']} release gates blocked.")
    for r in result:
        if r['status']=='FAIL':print(r['test'],r['detail'])
    return 1 if counts['FAIL'] else (2 if args.strict_release and counts['BLOCKED'] else 0)

if __name__=='__main__':sys.exit(main())
