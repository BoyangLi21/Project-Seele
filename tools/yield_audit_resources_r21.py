"""Temporarily park this task's read-only scans during native video capture."""
import ctypes,json,time,subprocess
from ctypes import wintypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/world_repair_r21'
def main():
 command="Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
 processes=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],creationflags=subprocess.CREATE_NO_WINDOW))
 watched=[p for p in processes if 'tools/run_native_checks_r21.py' in (p['CommandLine'] or '').replace('\\','/')]
 assert len(watched)==1,watched
 names={'tools/run_global_audits_r21.py','tools/render_world_maps_r21.py'}
 jobs=[p for p in processes if any(n in (p['CommandLine'] or '').replace('\\','/') for n in names)]
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);nt=ctypes.WinDLL('ntdll')
 kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
 kernel.CloseHandle.argtypes=[wintypes.HANDLE]
 kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
 nt.NtSuspendProcess.argtypes=nt.NtResumeProcess.argtypes=[wintypes.HANDLE]
 held=[];receipt=OUT/'audit_resource_pause.json'
 try:
  for p in jobs:
   handle=kernel.OpenProcess(0x0800,False,p['ProcessId']);assert handle
   assert nt.NtSuspendProcess(handle)==0;held.append((p['ProcessId'],handle))
  receipt.write_text(json.dumps(dict(paused=[p for p,h in held],until_native_review=watched[0]['ProcessId'],resumed=False),indent=2))
  deadline=time.monotonic()+1800
  watcher=kernel.OpenProcess(0x1000,False,watched[0]['ProcessId']);assert watcher
  code=wintypes.DWORD()
  while kernel.GetExitCodeProcess(watcher,ctypes.byref(code)) and code.value==259 and time.monotonic()<deadline:time.sleep(3)
  kernel.CloseHandle(watcher)
 finally:
  for pid,handle in held:nt.NtResumeProcess(handle);kernel.CloseHandle(handle)
  receipt.write_text(json.dumps(dict(jobs=[p for p,h in held],resumed=True),indent=2))
  print('Read-only audit workers resumed',flush=True)
if __name__=='__main__':main()
