#!/usr/bin/env python3
"""Minimal Android boot image v3 tool (no external dependencies).

  extract <boot.img> <outdir>   -> outdir/header.bin (first page) + outdir/ramdisk.img
  pack    --base <dir> --kernel <Image> --out <boot.img> [--pad N]

A v3 boot image is: 4096-byte page holding the header, then the kernel
(padded to 4096), then the ramdisk (padded to 4096). Nothing else.
"""
import argparse, os, struct, sys

PAGE = 4096
MAGIC = b"ANDROID!"
HDR_FMT_END = 44          # cmdline starts at offset 44 in a v3 header


def align(n, a=PAGE):
    return (n + a - 1) // a * a


def parse(hdr):
    if hdr[:8] != MAGIC:
        sys.exit("not an Android boot image (bad magic)")
    ksz, rsz, osv, hsz = struct.unpack_from("<4I", hdr, 8)
    ver, = struct.unpack_from("<I", hdr, 40)
    if ver != 3:
        sys.exit("header_version is %d, only v3 is supported" % ver)
    return ksz, rsz, osv, hsz


def cmd_extract(a):
    d = open(a.boot, "rb").read()
    ksz, rsz, _, _ = parse(d[:PAGE])
    r_off = PAGE + align(ksz)
    ramdisk = d[r_off:r_off + rsz]
    if len(ramdisk) != rsz:
        sys.exit("image truncated: ramdisk is %d bytes, header says %d" % (len(ramdisk), rsz))
    os.makedirs(a.outdir, exist_ok=True)
    open(os.path.join(a.outdir, "header.bin"), "wb").write(d[:PAGE])
    open(os.path.join(a.outdir, "ramdisk.img"), "wb").write(ramdisk)
    print("kernel_size=%d ramdisk_size=%d -> %s" % (ksz, rsz, a.outdir))


def cmd_pack(a):
    hdr = bytearray(open(os.path.join(a.base, "header.bin"), "rb").read())
    ramdisk = open(os.path.join(a.base, "ramdisk.img"), "rb").read()
    kernel = open(a.kernel, "rb").read()
    parse(bytes(hdr))
    if len(hdr) != PAGE:
        sys.exit("header.bin must be exactly %d bytes" % PAGE)
    if len(kernel) < 64 or kernel[56:60] != b"ARMd":
        sys.exit("kernel does not look like an arm64 Image (no ARMd magic at 0x38)")
    struct.pack_into("<2I", hdr, 8, len(kernel), len(ramdisk))
    out = bytes(hdr)
    out += kernel + b"\0" * (align(len(kernel)) - len(kernel))
    out += ramdisk + b"\0" * (align(len(ramdisk)) - len(ramdisk))
    if a.pad:
        if len(out) > a.pad:
            sys.exit("result (%d) is larger than --pad (%d)" % (len(out), a.pad))
        out += b"\0" * (a.pad - len(out))
    open(a.out, "wb").write(out)
    print("wrote %s: kernel=%d ramdisk=%d total=%d" % (a.out, len(kernel), len(ramdisk), len(out)))


def main():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    e = s.add_parser("extract"); e.add_argument("boot"); e.add_argument("outdir"); e.set_defaults(f=cmd_extract)
    k = s.add_parser("pack")
    k.add_argument("--base", required=True); k.add_argument("--kernel", required=True)
    k.add_argument("--out", required=True); k.add_argument("--pad", type=int, default=0)
    k.set_defaults(f=cmd_pack)
    a = p.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
