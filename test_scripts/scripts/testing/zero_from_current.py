import sys, math, yaml
def wrap(a):  # wrap to [-pi, pi]
    a = (a + math.pi) % (2*math.pi) - math.pi
    return a
if len(sys.argv)!=2:
    print("Usage: python3 scripts/zero_from_current.py <config.yaml>"); raise SystemExit(1)
p=sys.argv[1]
cfg=yaml.safe_load(open(p))
a=cfg["agent_params"]
sj=a.get("start_joints")
if not sj: raise SystemExit("start_joints missing/empty; run auto_gello_calibrate_sdk first.")
a["joint_offsets"]=[round(-wrap(x),6) for x in sj]
a["start_joints"]=[0]*len(sj)
yaml.safe_dump(cfg, open(p,"w"))
print("Updated", p)
print("joint_offsets:", a["joint_offsets"])
print("start_joints:", a["start_joints"])
