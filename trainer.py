"""Find a changing int32 in the arena and freeze it with Win32 APIs."""

import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import struct
import subprocess
import sys
from threading import Event, Thread


class ArenaLab:
    def __enter__(self):
        kernel = C.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (W.DWORD, W.BOOL, W.DWORD)
        kernel.OpenProcess.restype = W.HANDLE
        kernel.CloseHandle.argtypes = (W.HANDLE,)
        kernel.CloseHandle.restype = W.BOOL
        for api in (kernel.ReadProcessMemory, kernel.WriteProcessMemory):
            api.argtypes = (W.HANDLE, C.c_void_p, C.c_void_p, C.c_size_t,
                            C.POINTER(C.c_size_t))
            api.restype = W.BOOL
        self.kernel = kernel
        self.stop = Event()
        self.worker = None
        self.error = None
        self.handle = None
        self.child = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("arena.py")), "--lab"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        )
        try:
            address, size = self.child.stdout.readline().split()
            self.base, self.size = int(address, 16), int(size)
            # PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
            self.handle = kernel.OpenProcess(0x0010 | 0x0020 | 0x0008, False, self.child.pid)
            if not self.handle:
                raise C.WinError(C.get_last_error())
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        self.stop_freeze()
        if self.handle:
            self.kernel.CloseHandle(self.handle)
        try:
            self.child.communicate("quit\n", timeout=2)
        except subprocess.TimeoutExpired:
            self.child.kill()
            self.child.communicate()

    def exchange(self, action):
        self.child.stdin.write(action + "\n")
        self.child.stdin.flush()
        reply = self.child.stdout.readline().strip()
        if not reply:
            raise RuntimeError("O processo da arena encerrou.")
        return reply

    def transfer(self, api, address, buffer):
        size = C.sizeof(buffer)
        count = C.c_size_t()
        if not api(self.handle, address, C.byref(buffer), size, C.byref(count)):
            raise C.WinError(C.get_last_error())
        if count.value != size:
            raise OSError(f"Transferência parcial de memória ({count.value}/{size} bytes).")

    def snapshot(self):
        buffer = (C.c_ubyte * self.size)()
        self.transfer(self.kernel.ReadProcessMemory, self.base, buffer)
        return [value for (value,) in struct.iter_unpack("<i", buffer)]

    def find_health(self):
        self.stop_freeze()
        self.exchange("reset")
        before = self.snapshot()
        initial = [i for i, value in enumerate(before) if value == 100]
        self.exchange("hit")
        after = self.snapshot()
        matches = [i for i in initial if after[i] == 87]
        if len(matches) != 1:
            raise RuntimeError(f"A busca encontrou {len(matches)} candidatos após o dano.")
        self.health_address = self.base + matches[0] * 4
        return len(initial), self.health_address

    def start_freeze(self):
        self.stop_freeze()
        value = C.c_int32(100)
        self.transfer(self.kernel.WriteProcessMemory, self.health_address, value)
        self.error = None
        self.stop.clear()

        def freeze():
            try:
                while not self.stop.wait(0.03):
                    self.transfer(self.kernel.WriteProcessMemory, self.health_address, value)
            except OSError as error:
                self.error = error

        self.worker = Thread(target=freeze)
        self.worker.start()

    def stop_freeze(self):
        if self.worker is not None:
            self.stop.set()
            self.worker.join()
            self.worker = None


def main():
    if sys.platform != "win32":
        raise SystemExit("Este laboratório usa APIs do Windows.")
    with ArenaLab() as lab:
        print(f"ARENA // MEMORY LAB  |  PID {lab.child.pid}")
        print("Comandos  [scan] [freeze] [off] [hit] [fire] [status] [reset] [quit]")
        found = False
        while True:
            try:
                action = input("lab> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break
            if lab.error is not None:
                raise lab.error
            if action == "quit":
                break
            if action == "scan":
                candidates, address = lab.find_health()
                found = True
                print(f"{candidates} candidatos com HP 100 -> 1 com HP 87 | endereço 0x{address:X}")
            elif action == "freeze" and found:
                lab.start_freeze()
                print("Freeze ligado. O trainer reescreve HP = 100 a cada 30 ms.")
            elif action == "off":
                lab.stop_freeze()
                print("Freeze desligado.")
            elif action in {"hit", "fire", "status", "reset"}:
                print(lab.exchange(action))
            elif action == "freeze":
                print("Use scan primeiro.")
            else:
                print("Comando desconhecido.")


if __name__ == "__main__":
    main()
