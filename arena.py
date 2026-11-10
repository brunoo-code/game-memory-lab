"""Turn-based arena and controlled target for the lab."""

import ctypes
import secrets
import sys


def main():
    rng = secrets.SystemRandom()
    cells = (ctypes.c_int32 * 64)(*(rng.randrange(200, 10_000) for _ in range(64)))
    health, ammo, decoy_a, decoy_b = rng.sample(range(len(cells)), 4)
    for index in (health, decoy_a, decoy_b):
        cells[index] = 100
    cells[ammo] = 6
    drones = 3

    # In lab mode the target exposes the scan bounds, but no field offsets.
    if sys.argv[1:] == ["--lab"]:
        print(f"{ctypes.addressof(cells):x} {ctypes.sizeof(cells)}", flush=True)

    for line in sys.stdin:
        action = line.strip()
        if action == "quit":
            break
        if action == "reset":
            cells[health], cells[ammo], drones = 100, 6, 3
        elif action == "hit" and cells[health] > 0:
            cells[health] = max(0, cells[health] - 13)
        elif action == "fire" and drones and cells[health] > 0 and cells[ammo] > 0:
            cells[ammo] -= 1
            drones -= 1
            if drones:
                cells[health] = max(0, cells[health] - 35)
        print(f"HP {cells[health]:3} | municao {cells[ammo]} | drones {drones}", flush=True)


if __name__ == "__main__":
    main()
