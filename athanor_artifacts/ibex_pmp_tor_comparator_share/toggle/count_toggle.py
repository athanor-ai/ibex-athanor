import sys, re
vcd=open(sys.argv[1]).read()
# map var-id -> name; keep only dut port signals
idmap={}
for m in re.finditer(r'\$var \w+ \d+ (\S+) (\S+)', vcd):
    vid,name=m.group(1),m.group(2)
    idmap[vid]=name
ports={'csr_pmp_cfg_i','csr_pmp_addr_i','csr_pmp_mseccfg_i','debug_mode_i',
       'priv_mode_i','pmp_req_addr_i','pmp_req_type_i','pmp_req_err_o'}
# count value-change events on those ids after $dumpvars init
body=vcd.split('$enddefinitions')[1]
tog=0
for line in body.splitlines():
    line=line.strip()
    if not line or line.startswith('#') or line.startswith('$'): continue
    if line[0] in 'bB':
        parts=line.split()
        if len(parts)==2 and idmap.get(parts[1],'').split('[')[0] in ports: tog+=1
    elif line[0] in '01xzXZ':
        vid=line[1:]
        if idmap.get(vid,'').split('[')[0] in ports: tog+=1
print(tog)
