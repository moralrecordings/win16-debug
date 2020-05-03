Win16 reverse engineering tools
###############################


get_segtable.py
===============

Windows 3.1 uses a single shared segment table for all programs. In order to use the DOSBox debugger, you will need to know the mapping from the machine's 16-bit segment selectors (as seen in the CS/DS registers) to each segment in the target EXE or DLL.

The IBM PC does not have a flat addressing model; the underlying memory is paged, and can be mirrored all over the address space. In 16-bit protected mode, memory is accessed through segment selectors (13-bit index + 3-bit security flags), which the CPU maps to the linear address space via the Local Descriptor Table. Windows 3.1 takes full control of the Local Descriptor Table and allocating memory, so all the applications and DLLs in the current session will be jumbled in. However, we can take advantage of a few things:
  - Windows 3.1 stores a copy of the EXE header in memory, but with each of the file sections extended to include the segment selector.
  - The EXE header has to be accessible somewhere as a single continuous chunk of data.
  - It's possible to dump most of the linear address space that DOSBox uses as files.

This tool scrapes this mapping from DOSBox memory dumps taken with a running application, and provides the segment map information as JSON. In addition, a guess is provided for the segment ID and fake 32-bit offset that IDA Pro would use.

- Open the EXE in your favourite disassembler with NE support (e.g. IDA Pro)
- Open DOSBox, start Windows 3.1, and then immediately start your target application. I recommend adding a shortcut to Program Manager.
- When the application is running, activate the DOSBox debugger with Alt + Pause
- In the debugger, type "CPU" and press Enter. The last line of the log should describe the Local Descriptor Table (e.g. "MISC:LDT selector=0070, base=80B1B000 limit=00002FFF*1").
- In the debugger, type "MEMDUMPBIN 0000 00000000 2000000" and press Enter. A file called "MEMDUMP.BIN" will be created in the directory that DOSBox was executed from; rename this file to e.g. "memory_low.bin".
- Repeat with "MEMDUMPBIN 0000 80000000 1000000". Rename this file to e.g. "memory_high.bin".
- You can now run get_segtable.py:
  - First argument will be the base address to the LDT (in this case, 0x80B1B000).
  - Second argument will be the full Windows path to the executable, (e.g. "C:\\DIRECTOR\\DIRECTOR.EXE").
  - Third and fourth arguments will be the path of the two memory dump files (e.g. "./memory_low.bin" "./memory_high.bin")


convert_log.py
==============

CPU coverage logging for DOSBox has been `added as of revision 4318 <https://sourceforge.net/p/dosbox/patches/282/>`_.

IDA Pro uses a fake 32-bit memory map to lay out 16-bit code. In order to use a CPU coverage map from DOSBox with Lighthouse, addresses need to be converted from seg:offset_16 format to module+offset_32. This tool converts CPU coverage logs from DOSBox to the Lighthouse expected format using the JSON segment map from get_segtable.py.


optloader.py
============

Win16 editions of Macromedia Director and Macromedia Projector were linked with `OPTLINK <https://digitalmars.com/ctg/optlink.html>`_, which uses an executable packer known as OPTLOADER. OPTLOADER does a lot of horrible things, including:

- Splitting the code across hundreds of tiny segments, instead of a handful of fully-sized ones.
- Compressing every segment with a homemade RLE compression scheme.
- Use Win16's undocumented "Self-Loading Windows Applications" mode to bypass the Windows kernel's EXE loading code.
- Provides a first stage decompression stub (BootApp) that unpacks a second stage loader which unpacks each segment on demand (LoadAppSeg).
- Despite segment boundaries being well defined, the compression algorithm ignores these and expects to read earlier, unrelated bits of file for the RLE.
- When each segment gets accessed for the first time, the second stage loader has to unpack the compressed code *and* manually apply all of the relocations (e.g. segment IDs, offsets, floating point instructions).
- The relocations are stored in a completely different format to a standard Win16 executable.
- The combination of on-demand loading, hundreds of segments, and hundreds of relocations per segment, makes it near impossible to extract a working Win16 executable from a memory dump.

All of these made Macromedia Director a royal pain to reverse engineer. After a few unsuccessful attempts to rip a program from memory, I settled for modelling as much of the Win16 NE file specification in `Mr. Crowbar <https://moral.net.au/mrcrowbar>`_ as humanly possible. As it turns out NE is an absolutely bonkers format that uses every addressing scheme and data structure under the sun, so I think I came out very slightly ahead in terms of effort vs. cutting up the file by hand.

optloader.py does the following:

- Opens the source executable with Mr. Crowbar's lib.os.win16.EXE model.
- Decompresses each segment and the list of relocations with a rickety port of the RLE unpacker.
- Makes a corrected segment table and replaces the one in the EXE.
- Saves the result to another EXE file, which should now be openable in IDA Pro.
