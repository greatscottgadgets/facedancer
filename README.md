# FaceDancer 2.2

This repository houses the next generation of FaceDancer software. Descended from
the original GoodFET-based FaceDancer, this repository provides a python module 
that provides expanded FaceDancer support-- including support for multiple boards 
and some pretty significant new features.

## What is a FaceDancer?

FaceDancer boards are simple hardware devices that act as "remote-controlled" USB
controllers. With the proper software, you can use these boards to quickly and
easily emulate USB devices-- and to fuzz USB host controllers!

This particular software repository currently allows you to easily create emulations
of USB devices in Python. Control is fine-grained enough that you can cause all
kinds of USB misbehaviors. :)

For more information, see:

 * [Travis Goodspeed's blog post on FaceDancer](http://travisgoodspeed.blogspot.com/2012/07/emulating-usb-devices-with-python.html)
 * [The FaceDancer 21, the original supported board](http://goodfet.sourceforge.net/hardware/facedancer21/)

## USBProxy 'Nouveau' and Protocol Analysis

A major new feature of the newer FaceDancer codebase is the ability to man-in-the
middle USB connections-- replacing one of the authors' original [USBProxy](https://github.com/dominicgs/usbproxy)
project. This opens up a whole new realm of applications-- including protocol analysis
and live manipulation of USB packets-- and is especially useful when you don't control
the software running on the target device (e.g. on embedded systems or games consoles).

```
                 +-----------------------------------------------------------------------+
+------------+   |  +--------------------------------+   +---------------------------+   |  +--------------+
|            |   |  |                                |   |                           |   |  |              |
|  PROXIED   |   |  |         HOST COMPUTER          |   |    FACEDANCER DEVICE      |   |  |  TARGET USB  |
|   DEVICE   <------>  running FaceDancer software   <--->  acts as USB-Controlled   <------>     HOST     |
|            |   |  |                                |   |      USB Controller       |   |  |              |
|            |   |  |                                |   |                           |   |  |              |
+------------+   |  +--------------------------------+   +---------------------------+   |  +--------------+
                 |                                                                       |
                 |                    MITM Setup (HOST + FACEDANCER)                     |
                 +-----------------------------------------------------------------------+
```


This feature is complete, but could use more documentation. Pull requests are welcome. :)


## How do I use this repository?

First, you'll likely want to set the ```BACKEND``` environment variable, which lets
the software know which type of FaceDancer board you'd like to use. If this variable
isn't set, the software will try to guess for you based on what's connected. It doesn't
always make the best guesses, so you're probably better off setting it yourself.

Next, you can run any of the pre-made scripts, e.g. ```facedancer-serial.py```.

For example:

```sh
export BACKEND=goodfet
./facedancer-serial.py
```

## What boards are currently supported?

 * All GoodFET-based facedancers, including the common FaceDancer21 (```BACKEND=goodfet```)
 * The [GreatFET One](http://greatscottgadgets.com/greatfet/) (```BACKEND=greatfet```)
 * The NXP LPC4330 Xplorer board (```BACKEND=greatfet```)
 * The CCCamp 2015 rad1o badge with GreatFET l0adable (```BACKEND=greatfet```)
 * RPi + Max3241 Raspdancer boards (```BACKEND=raspdancer```)

Note that hardware restrictions prevent the MAX3420/MAX3421 boards from emulating
more complex devices-- there's limitation on the number/type of endpoints that can be
set up. The LPC4330 boards-- such as the GreatFET-- don't suffer these limitations.

For a similar reason, the MAX3420/MAX3421 boards (`BACKEND=goodfet` or `BACKEND=raspdancer`)
currently cannot be used as USBProxy-nv MITM devices. All modern boards (`BACKEND=greatfet`)
should be fully functional.

## What boards could be supported soon?

 * Any Linux computer with gadgetfs support (e.g. the Pi Zero or Beaglebone Black)

## What features do you plan on adding?

The roadmap is hazy, but in addition to multi-board support, this repository
eventually will be home to some cool new features, such as:

 * High-speed ("USB 2.0") device emulation on devices with USB 2.0 PHYS

## Whose fault _is_ this?

There are a lot of people to blame for the awesomeness that is this repo,
including:

 * Travis Goodspeed (@travisgoodspeed)
 * Sergey Bratus (@sergeybratus)
 * ktemkin (@ktemkin)
 * Dominic Spill (@dominicgs)
 * Michael Ossmann (@michaelossmann)
 * anyone whose name appears in the git history :)

## Contributions?

... are always welcome. Shoot us a PR!
