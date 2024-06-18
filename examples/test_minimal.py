import logging

def main():
    import asyncio
    import usb1

    VENDOR_REQUEST    = 0x65
    MAX_TRANSFER_SIZE = 64

    with usb1.USBContext() as context:
        #logging.info("Host: waiting for device to connect")
        #await asyncio.sleep(1)

        device_handle = context.openByVendorIDAndProductID(0x1209, 0x0001)
        if device_handle is None:
            raise Exception("device not found")
        device_handle.claimInterface(0)

        # test IN endpoint
        logging.info("Testing bulk IN endpoint")
        response = device_handle.bulkRead(
            endpoint = 0x81,
            length   = MAX_TRANSFER_SIZE,
            timeout  = 1000,
        )
        logging.info(f"[host] received '{response}' from bulk endpoint")
        print("")

        # test OUT endpoint
        logging.info("Testing bulk OUT endpoint")
        response = device_handle.bulkWrite(
            endpoint = 0x01,
            data     = b"host say oh hai on bulk endpoint",
            timeout  = 1000,
        )
        print(f"sent {response} bytes\n")

        # test IN vendor request handler
        logging.info("Testing IN control transfer")
        response = device_handle.controlRead(
            request_type = usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE,
            request      = 1,
            index        = 2,
            value        = 3,
            length       = MAX_TRANSFER_SIZE,
            timeout      = 1000,
        )
        logging.info(f"[host] received '{response}' from control endpoint")
        print("")

        # test OUT vendor request handler
        logging.info("Testing OUT control transfer")
        response = device_handle.controlWrite(
            request_type = usb1.TYPE_VENDOR | usb1.RECIPIENT_DEVICE,
            request      = 2,
            index        = 3,
            value        = 4,
            data         = b"host say oh hai on control endpoint",
            timeout      = 1000,
        )
        print(f"sent {response} bytes\n")


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    main()
