#!/usr/bin/env python3
import argparse

from mrcrowbar import models as mrc, utils
from mrcrowbar.lib.hardware import ibm_pc
from mrcrowbar.lib.os import win16

def get_local_offset( memory_map, offset ):
    for start, mem in memory_map.items():
        if offset in range( start, start + len( mem ) ):
            return start, offset-start
    raise ValueError


# dump the local descriptor table
def get_ldt( memory_map, base, limit ):
    bank, rel_base = get_local_offset( memory_map, base )
    return ibm_pc.SegmentDescriptorTable( memory_map[bank][rel_base:][:limit+1] )


# scrape a memory dump for an EXE's module table
# basically, search for the EXE's full path, then check if there's an NE header attached
def find_module_table( memory_map, app_path ):
    MAX_LOOKBACK = 0x1000
    
    for base, mem in memory_map.items():
        matches = [x for x in utils.find_all_iter( mem, app_path ) if mem[x-8] == len( app_path )+7 ]
        for m in matches:
            lookback = m-MAX_LOOKBACK
            ne_matches = [x for x in utils.find_all_iter( mem, b'NE', start=lookback, end=m ) if (x % 32) == 0]
            if ne_matches:
                return base + ne_matches[-1]
    raise ValueError( 'Could not find a Win16 module table for {}'.format( app_path ) )


# dump an EXE's module table
def get_module_table( memory_map, offset ):
    bank, rel_offset = get_local_offset( memory_map, offset )
    return win16.ModuleTable( memory_map[bank][rel_offset:] )



# should always be the same for win3.1?
LDT_BASE, LDT_LIMIT = 0x80BAD000, 0x2FFF

DESCRIPTION = 'Extract the Win16 segment table from a DOSBox memory dump.'
EPILOG = """Windows 3.1 uses a single shared segment table for all programs. In order to use the DOSBox debugger, you will need to know which segment ID maps to a segment in the target EXE or DLL. This tool scrapes this mapping from memory dumps of a running application
"""

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description=DESCRIPTION, epilog=EPILOG )
    parser.add_argument( 'exe_path', help='Full DOSBox path to the EXE (e.g. "C:\\\\WINDOWS\\\\PROGMAN.EXE")' )
    parser.add_argument( 'mem_low', type=argparse.FileType( mode='rb' ), help='Memory dump of the low range: MEMDUMPBIN 0000 00000000 2000000' )
    parser.add_argument( 'mem_high', type=argparse.FileType( mode='rb' ), help='Memory dump of the high range: MEMDUMPBIN 0000 80000000 1000000' )
    #parser.add_argument( '--offsets', help='Comma-seperated list of IDA offsets for each segment', required=False )
    #parser.add_argument( '--in_file', type=argparse.FileType( mode='r' ), help='Input DOSBox LOGC data for processing', required=False )
    #parser.add_argument( '--out_file', type=argparse.FileType( mode='w' ), help='Output file for Lighthouse in mod+off format', required=False )
    args = parser.parse_args()

    exe_path = args.exe_path.upper().encode( 'cp1252' )+b'\x00'
    memory_map = {
        0x00000000: args.mem_low.read(),
        0x80000000: args.mem_high.read()
    }

    # fish out the local descriptor table from the memory dump.
    # this is used by the x86 chip to map segment selectors to memory in protected mode.
    ldt_dir = get_ldt( memory_map, LDT_BASE, LDT_LIMIT )

    # fish out the Win16 program's module table from the memory dump.
    # every Win16 app has one of these, which is very similar to the NE header
    # in the executable EXCEPT the segment table in this will tell us what
    # segments in the EXE are mapped to what LDT entry.
    modtable_loc = find_module_table( memory_map, exe_path )
    print( 'Module table for executable found at 0x{:08x}'.format( modtable_loc ) )

    modtable = get_module_table( memory_map, modtable_loc )

    #seg_map = {}
    ida_list = []
    seg_list = []
    for i, s in enumerate( modtable.ne_header.segtable ):
        ida_name = '{}seg{:02}'.format( 'c' if ldt_dir.seglist[s.selector >> 3].code_seg else 'd', i+1 )
        seg_id = '{:04x}'.format( s.selector | 7 ).upper()
        #seg_map[seg_id] = ida_name
        seg_list.append( seg_id )
        ida_list.append( ida_name )
        print( '{} -> {:04x} -> {}'.format( i+1, s.selector | 7, ldt_dir.seglist[s.selector >> 3] ) )

    print( seg_list )
    print( ida_list )

    
