#!/usr/bin/env python3
import argparse

from mrcrowbar import utils
from mrcrowbar.lib.os import win16
from mrcrowbar import models as mrc

class Flags:
    def __init__( self ):
        self.carry = False
        self.overflow = False
        self.zero = False
        self.sign = False
    
    def __repr__( self ):
        return 'carry={}, overflow={}, zero={}, sign={}'.format( self.carry, self.overflow, self.zero, self.sign )
     

class Register:
    def __init__( self, size=2, flags=None ):
        self.size = size*8
        self.value = 0
        self.flags = flags if flags else Flags()

    def _validate( self, value ):
        assert 0 <= value < (1 << self.size)

    def mov( self, value ):
        self._validate( value )
        self.value = value

    def inc( self, value=1 ):
        self._validate( value )
        of_test1 = bool(self.value & (1 << (self.size-1)))
        of_test2 = bool(value & (1 << (self.size-1)))
        self.value += value
        self.value %= (1 << self.size)
        of_test3 = bool(self.value & (1 << (self.size-1)))
        self.flags.overflow = (of_test1 == of_test2) and (of_test1 != of_test3)
        self.flags.zero = self.value == 0
        self.flags.sign = bool(self.value & (1 << (self.size-1)))

    def dec( self, value=1 ):
        self._validate( value )
        of_test1 = bool(self.value & (1 << (self.size-1)))
        of_test2 = not bool(value & (1 << (self.size-1)))
        self.value -= value
        self.value %= (1 << self.size)
        of_test3 = bool(self.value & (1 << (self.size-1)))
        self.flags.overflow = (of_test1 == of_test2) and (of_test1 != of_test3)
        self.flags.zero = self.value == 0
        self.flags.sign = bool(self.value & (1 << (self.size-1)))

    def add( self, value ):
        self._validate( value )
        of_test1 = bool(self.value & (1 << (self.size-1)))
        of_test2 = bool(value & (1 << (self.size-1)))
        self.value += value
        self.flags.carry = (self.value < 0) or (self.value >= (1 << self.size))
        self.value %= (1 << self.size)
        of_test3 = bool(self.value & (1 << (self.size-1)))
        self.flags.overflow = (of_test1 == of_test2) and (of_test1 != of_test3)
        self.flags.zero = self.value == 0
        self.flags.sign = bool(self.value & (1 << (self.size-1)))

    def sub( self, value ):
        self._validate( value )
        of_test1 = bool(self.value & (1 << (self.size-1)))
        of_test2 = not bool(value & (1 << (self.size-1)))
        self.value -= value
        self.flags.carry = (self.value < 0) or (self.value >= (1 << self.size))
        self.value %= (1 << self.size)
        of_test3 = bool(self.value & (1 << (self.size-1)))
        self.flags.overflow = (of_test1 == of_test2) and (of_test1 != of_test3)        
        self.flags.zero = self.value == 0
        self.flags.sign = bool(self.value & (1 << (self.size-1)))

def cmp( op1, op2, size=2 ):
    src = Register( size=size )
    src.mov( op1 )
    src.sub( op2 )
    return src.flags
    

def optloader_precopy(data, start_offset, precopy_offset, precopy_size):
    si = start_offset 
    di = precopy_offset
    cx = precopy_size

    di += precopy_size - 1
    si += precopy_size - 1
    for i in range(precopy_size):
        data[di] = data[si]
        di -= 1
        si -= 1
    #print('INITIAL COPY: data[0x{:04x}:0x{:04x}] = data[0x{:04x}:0x{:04x}]'.format(di+1, di+1+cx, si+1, si+1+cx))
    #utils.hexdump(data)



def optloader_reverse(src, read_offset, dest, write_offset):
    global bp, dx, si
    #utils.hexdump(src)
    flags = Flags()
    si = 0
    di = 0
    bl = 0
    bh = 0

    bp = Register(flags=flags)
    dx = 0x10
    si = read_offset
    di = write_offset
    #print('di=0x{:04x}, si=0x{:04x}'.format(di, si))    

    # sub_31
    bp.mov( utils.from_uint16_le(src[si:si+2]) )
    si += 2
    cx = 0
    
    # loc_62
    while True:
        #print('==== dx: {:04x}, si: {:04x}, di: {:04x}, bp: {:04x}'.format(dx, si, di, bp.value))
        # PROBLEM
        #if di == 0x40b7:
        #    import pdb; pdb.set_trace()


        if (get_bit(src)):
            # loc_61
            dest[di] = src[si]
            #print('di=0x{:04x}, si=0x{:04x}, dest[0x{:04x}] = src[0x{:04x}] = {}'.format(di, si, di, si, src[si:si+1].hex()))
            di += 1
            si += 1
            continue

        # loc_69

        branch1 = 1
        branch2 = 0

        # loc_6E
        if (get_bit(src)):
            # loc_CB
            cx += 1
            if (get_bit(src)):
                cx += 1
                if (get_bit(src)):
                    # loc_D9
                    bh = 0x08
                    bl = 0x02
                    if (get_bit(src)):
                        bh = 0x0C
                        bl = 0x03
                        if (get_bit(src)):
                            cx = src[si]
                            si += 1
                            flags = cmp( cx, 0x81 )
                            if (flags.carry):
                                pass
                            elif (not flags.zero):
                                #print('EXIT CONDITION: src[0x{:04x}] == 0x{:02x}'.format(si-1, cx))
                                return si
                            else:
                                cx = 0
                                continue
                        else:
                            # loc_138
                            cx = 0
                            while (bl != 0):
                                # loc_13A
                                # loc_13F
                                cx += cx + get_bit(src)
                                bl -= 1
                            # loc_145
                            cx += bh

                    else:
                        # loc_138
                        cx = 0
                        while (bl != 0):
                            # loc_13A
                            # loc_13F
                            cx += cx + get_bit(src)
                            bl -= 1
                        # loc_145
                        cx += bh

                else:
                    branch2 = 1
            else:
                branch2 = 1
        else:
            bh = 0
            branch2 = 1


        if branch2:
            # loc_72
            cx += 1
            cx += cx + get_bit(src)
                
            if (cx == 2):
                branch1 = 0


        if (branch1):
            # loc_7F
            bh = 0

            skip_inc = False
            if get_bit(src):
                # loc_FD
                if get_bit(src):
                    ch = 0x10
                    cl = 0x04
                    if get_bit(src):
                        ch = 0x20
                        cl = 0x04
                        if get_bit(src):
                            ch = 0x30
                            cl = 0x04
                            if get_bit(src):
                                ch = 0x40
                                cl = 0x06
                else:
                    ch = 0x04
                    cl = 0x02
                    if get_bit(src):
                        ch = 0x08
                        cl = 0x03
            else:
                # loc_87
                if get_bit(src):
                    # loc_AE
                    bh += 1
                    # loc_B5
                    if get_bit(src):
                        ch = 0x02
                        cl = 0x01
                    else:
                        skip_inc = True
                else: 
                    skip_inc = True

            if not skip_inc:
                # loc_BA
                bh = 0

                # loc_BC
                while (cl != 0):
                    bh += bh + get_bit(src)
                    cl -= 1
                bh += ch

        # loc_91
        bl = src[si]
        si += 1
        bl ^= 0xff
        bh ^= 0xff
        old_di = di
        old_si = si
        #import pdb; pdb.set_trace()
        si = (di+ (bh << 8) + bl) & 0xffff
        for i in range(cx):
            dest[di] = dest[si]
            di += 1
            si += 1
        #print('di=0x{:04x}, si=0x{:04x}, dest[0x{:04x}:0x{:04x}] = src[0x{:04x}:0x{:04x}] = {}'.format(old_di, old_si, old_di, old_di+cx, si-cx, si, dest[old_di:old_di+cx].hex()))
        cx = 0
        si = old_si


def get_bit(src):
    global bp, dx, si
    bp.add( bp.value )
    dx -= 1
    if (dx == 0):
        bp.mov( utils.from_uint16_le(src[si:si+2]) )
        dx = 0x10
        si += 2
    res = 1 if bp.flags.carry else 0
    #print(res)
    return res


def optloader_get_relocs( raw, relocs_offset, relocs_count ):
    si = relocs_offset
    #import pdb; pdb.set_trace()
    def get_selector(al):
        al -= 1
        al += ax # base 0, stride 10
        bx = ax
        ax <<= 2
        bx += ax

    result = win16.RelocationTable()
    result.reltable = []


    #print('relocs_count: {}'.format(relocs_count))
    while relocs_count > 0:
        #print('START - si: {:04x}'.format(si))
        al = raw[si]
        ah = raw[si+1]
        si += 2
        num_items = ah
        relocs_count -= num_items
        #print('relocs_count: {} ({})'.format(relocs_count, -num_items))
        if al == 0xf0:
            # special base type
            #print('BASE TYPE')
            for i in range( num_items ):
                al = raw[si]
                di = utils.from_uint16_le( raw[si+1:si+3] )
                #print( 'al: {:02x}, di: {:04x}'.format( al, di ) )
                si += 3
                reloc = win16.Relocation( parent=result )
                reloc.address_type = win16.RelocationAddressType.SELECTOR_16
                reloc.detail_type = win16.RelocationDetail.INTERNAL_REF
                reloc.offset = di
                reloc.detail = win16.RelocationInternalRef( parent=reloc )
                reloc.detail.index = al
                result.reltable.append( reloc )
        else:
            tgt_type = al & 0x7
            #print('target type: {:02x}'.format(tgt_type) )

            src_type = (al >> 3) & 0x3
            #print('source type: {:02x}'.format(src_type) )
            
            TGT_TYPES = [
                win16.RelocationAddressType.LOW_BYTE,
                win16.RelocationAddressType.SELECTOR_16,
                win16.RelocationAddressType.POINTER_32,
                win16.RelocationAddressType.OFFSET_16,
            ]

            reloc_base = win16.Relocation()
            reloc_base.address_type = TGT_TYPES[tgt_type & 3]
            reloc_base.additive = 1 if (tgt_type & 4) else 0

            if src_type == 0x00:
                #print('RELOC_SRC_INTERNAL')
                al = raw[si]
                si += 1
                #print('seg ID: {}'.format(al))
                if al != 0xff:
                    loops = 1
                else:
                    loops = num_items

                for i in range( loops ):
                    di = utils.from_uint16_le( raw[si:si+2] )
                    dx = utils.from_uint16_le( raw[si+2:si+4] )
                    si += 4
                    #print('di: {:04x}, dx: {:04x}'.format(di, dx))
                    # call the target func
                    new_reloc = win16.Relocation( reloc_base, parent=result )
                    new_reloc.detail_type = win16.RelocationDetail.INTERNAL_REF
                    new_reloc.offset = di
                    new_reloc.detail = win16.RelocationInternalRef( parent=new_reloc )
                    new_reloc.detail.index = al
                    result.reltable.append( new_reloc )


            elif src_type == 0x01:
                #print('RELOC_SRC_ORDINAL')
                ax = utils.from_uint16_le( raw[si:si+2] )
                #print('modref ID: {}'.format(ax))
                si += 2
                for i in range( num_items ):
                    di = utils.from_uint16_le( raw[si:si+2] )
                    dx = utils.from_uint16_le( raw[si+2:si+4] )
                    si += 4
                    #print('di: {:04x}, dx: {:04x}'.format(di, dx))
                    # call the target func
                    new_reloc = win16.Relocation( reloc_base, parent=result )
                    new_reloc.detail_type = win16.RelocationDetail.IMPORT_ORDINAL
                    new_reloc.offset = di
                    new_reloc.detail = win16.RelocationImportOrdinal( parent=new_reloc )
                    new_reloc.detail.index = ax
                    new_reloc.detail.ordinal = dx
                    result.reltable.append( new_reloc )


            elif src_type == 0x02:
                #print('RELOC_SRC_NAME')
                ax = utils.from_uint16_le( raw[si:si+2] )
                #print('modref ID: {}'.format(ax))
                si += 2
                for i in range( num_items ):
                    di = utils.from_uint16_le( raw[si:si+2] )
                    bx = utils.from_uint16_le( raw[si+2:si+4] )
                    si += 4
                    #print('di: {:04x}, dx: {:04x}'.format(di, bx))
                    # call the target func
                    new_reloc = win16.Relocation(reloc_base, parent=result )
                    new_reloc.detail_type = win16.RelocationDetail.IMPORT_NAME
                    new_reloc.offset = di
                    new_reloc.detail = win16.RelocationImportName( parent=new_reloc )
                    new_reloc.detail.index = ax
                    new_reloc.detail.name_offset = bx
                    result.reltable.append( new_reloc )


            elif src_type == 0x03:
                #print('RELOC_SRC_OSFLOAT')
                ax = utils.from_uint16_le( raw[si:si+2] )
                si += 2
                for i in range( num_items ):
                    di = utils.from_uint16_le( raw[si:si+2] )
                    si += 2
                    new_reloc = win16.Relocation(reloc_base, parent=result )
                    new_reloc.detail_type = win16.RelocationDetail.OS_FIXUP
                    new_reloc.offset = di
                    new_reloc.detail = win16.RelocationOSFixup( parent=new_reloc )
                    new_reloc.detail.fixup = win16.RelocationOSFixupType( ax )
                    result.reltable.append( new_reloc )

            else:
                print('unknown src type? {:02x}'.format(src_type))
    return result



def optloader_unpack( in_file ):
    if in_file[0:2] != b'MZ':
        raise ValueError( 'Input file is not a Win16 executable - MZ header missing' )
    ne_offset = utils.from_uint16_le( in_file[0x3c:0x3e] )
    if in_file[ne_offset:ne_offset+2] != b'NE':
        raise ValueError( 'Input file is not a Win16 executable - NE header missing' )

    e = win16.EXE( in_file )

    unpacked = []

    # special treatment for segment 1, which unpacks itself
    seg1_raw = in_file[e.ne_header.segtable[0].offset:][:e.ne_header.segtable[0].size]
    if seg1_raw[0x17f:0x1be] != b'OPTLOADER - Copyright (C) 1993 SLR Systems\nAll Rights Reserved\x00':
        raise ValueError( 'Input file is not an OPTLOADER compressed executable' )

    seg1 = bytearray( e.ne_header.segtable[0].alloc_size )
    seg1[:len( seg1_raw )] = seg1_raw

    start_offset = utils.from_uint16_le( seg1[0x08:0x0a] )
    precopy_size = utils.from_uint16_le( seg1[0x2e:0x30] )
    alloc_size = e.ne_header.segtable[0].alloc_size
    optloader_precopy( seg1, start_offset=start_offset, precopy_offset=alloc_size-precopy_size, precopy_size=precopy_size )
    optloader_reverse( src=seg1, read_offset=alloc_size-precopy_size, dest=seg1, write_offset=start_offset )

    # patch out hints to use insane loader in the header
    #seg1[0x00:0x18] = b'\x00'*0x18
    unpacked.append( (seg1, []) )

    # now for the rest of the crap
    for i, seg in enumerate( e.ne_header.segtable[1:] ):
        # would you believe, the compression in this thing
        # relies on the random contents of whatever's in the EXE 
        # between the 512 byte sector boundary and the start of
        # the segment! utterly cooked
        predelta = seg.offset & 0x1ff
        postdelta = 512-((seg.size+predelta) % 512)
        raw = in_file[seg.offset & 0xfffffe00:][:seg.size+predelta+postdelta]
        seg_out = bytearray( seg.alloc_size )

        start_offset = predelta
        relocs_count = utils.from_uint16_le( raw[start_offset:start_offset+2] )
        start_offset += 2
        relocs_offset = optloader_reverse( raw, start_offset, seg_out, 0 )
        relocs = optloader_get_relocs( raw, relocs_offset, relocs_count )
        unpacked.append( (seg_out, relocs) )

    # load segments back into exe
    e.ne_header.flags &= 0xf7ff
    for i, x in enumerate( unpacked ):
        e.ne_header.segtable[i].segment.data = x[0]
        e.ne_header.segtable[i].iterated = 0
        if x[1]:
            e.ne_header.segtable[i].relocations = 1
            e.ne_header.segtable[i].segment.relocations = x[1]
    e.segdatastore.save()

    return e


DESCRIPTION = 'Unpack an obfuscated Win16 executable packed by OPTLOADER.'

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description=DESCRIPTION )
    parser.add_argument( 'source', type=argparse.FileType( mode='rb' ), help='Source EXE file.' )
    parser.add_argument( 'target', type=argparse.FileType( mode='wb' ), help='Target EXE file.' )
    args = parser.parse_args()

    result = optloader_unpack( args.source.read() )
    args.target.write( result.export_data() )

