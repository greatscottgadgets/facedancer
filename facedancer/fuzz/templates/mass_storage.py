'''
Mass storage device specific templates
'''
from kitty.model import Template, Pad
from kitty.model import String, UInt8, BE32, BE16, RandomBytes
from kitty.model import SizeInBytes
from generic import SizedPt

# TODO: scsi_test_unit_ready_response (nothing to fuzz! no data returned, besides the csw)
# TODO: scsi_send_diagnostic_response
# TODO: scsi_prevent_allow_medium_removal_response
# TODO: scsi_write_10_response (nothing to fuzz! no data returned, besides the csw)
# TODO: scsi_write_6_response
# TODO: scsi_read_6_response
# TODO: scsi_verify_10_response


# USBMassStorageClass
msc_get_max_lun_response = Template(
    name='msc_get_max_lun_response',
    fields=UInt8(name='Max_LUN', value=0x00))


# Request Sense - FuzzableUSBMassStorageInterface
scsi_request_sense_response = Template(
    name='scsi_request_sense_response',
    fields=[
        UInt8(name='ResponseCode', value=0x70),
        UInt8(name='VALID', value=0x00),
        UInt8(name='Obsolete', value=0x00),
        UInt8(name='SenseKey', value=0x00),
        UInt8(name='Resv', value=0x00),
        UInt8(name='ILI', value=0x00),
        UInt8(name='EOM', value=0x00),
        UInt8(name='FILEMARK', value=0x00),
        BE32(name='Information', value=0x00),
        SizedPt(
            name='Additional_Sense_data',
            fields=[
                BE32(name='CmdSpecificInfo', value=0x00),
                UInt8(name='ASC', value=0x00),
                UInt8(name='ASCQ', value=0x00),
                UInt8(name='FRUC', value=0x00),
                UInt8(name='SenseKeySpecific_0', value=0x00),
                UInt8(name='SenseKeySpecific_1', value=0x00),
                UInt8(name='SenseKeySpecific_2', value=0x00),
            ])
    ])


# Inquiry - FuzzableUSBMassStorageInterface
scsi_inquiry_response = Template(
    name='scsi_inquiry_response',
    fields=[
        UInt8(name='Peripheral', value=0x00),
        UInt8(name='Removable', value=0x80),
        UInt8(name='Version', value=0x04),
        UInt8(name='Response_Data_Format', value=0x02),
        SizeInBytes(
            name='Additional Length',
            sized_field='Additional Inquiry Data',
            length=8
        ),
        SizedPt(name='Additional Inquiry Data',
                fields=[
                    UInt8(name='Sccstp', value=0x00),
                    UInt8(name='Bqueetc', value=0x00),
                    UInt8(name='CmdQue', value=0x00),
                    Pad(8 * 8, fields=String(name='VendorID', value='Paul', max_size=8)),
                    Pad(16 * 8, fields=String(name='ProductID', value='Atreides', max_size=16)),
                    Pad(4 * 8, fields=String(name='productRev', value='1718', max_size=4)),
                ])
    ])


# Mode Sense - FuzzableUSBMassStorageInterface
scsi_mode_sense_6_response = Template(
    name='scsi_mode_sense_6_response',
    fields=[
        SizeInBytes(name='bLength', sized_field='scsi_mode_sense_6_response', length=8, fuzzable=True),
        UInt8(name='MediumType', value=0x00),
        UInt8(name='Device_Specific_Param', value=0x00),
        SizedPt(name='Mode_Parameter_Container', fields=RandomBytes(name='Mode_Parameter', min_length=0, max_length=4, value='\x1c'))
    ])


# Mode Sense - FuzzableUSBMassStorageInterface
scsi_mode_sense_10_response = Template(
    name='scsi_mode_sense_10_response',
    fields=[
        SizeInBytes(name='bLength', sized_field='scsi_mode_sense_10_response', length=8, fuzzable=True),
        UInt8(name='MediumType', value=0x00),
        UInt8(name='Device_Specific_Param', value=0x00),
        SizedPt(name='Mode_Parameter_Container', fields=RandomBytes(name='Mode_Parameter', min_length=0, max_length=4, value='\x1c'))
    ])


# Read Format Capacity - FuzzableUSBMassStorageInterface
scsi_read_format_capacities = Template(
    name='scsi_read_format_capacities',
    fields=[
        BE32(name='capacity_list_length', value=0x8),
        BE32(name='num_of_blocks', value=0x1000),
        BE16(name='descriptor_code', value=0x1000),
        BE16(name='block_length', value=0x0200)
    ])


# Read Capacity - FuzzableUSBMassStorageInterface
scsi_read_capacity_10_response = Template(
    name='scsi_read_capacity_10_response',
    fields=[
        BE32(name='NumBlocks', value=0x4fff),
        BE32(name='BlockLen', value=0x200)
    ])
