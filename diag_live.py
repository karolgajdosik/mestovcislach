import sys, subprocess
subprocess.run(["pip","install","-q","-r","scripts/requirements.txt"])
sys.path.insert(0,"scripts")
import hlasovania_web as hw, zber_samosprava_mesta as zs
print("BA obdobia:", hw.vol_obdobia())
print("KE datasety:", zs.datasety_hlasovani(zs.MESTA["kosice"]))
print("HOTOVO")
