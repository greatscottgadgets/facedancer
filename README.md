# FaceDancer pre-2.0

This repository houses what will hopefully be the next generation of FaceDancer
software. Descended from the original GoodFET-based Facedancer, this repository
provides a python module that provides expanded facedancer support-- including
support for multiple boards and a variety of new features.

## What is a FaceDancer?

FaceDancer boards are simple hardware devices that act as "remote-controlled" USB
controllers. With the proper software, you can use these boards to quickly and
easily emulate USB devices-- and to fuzz USB host controllers!

This particular software repository currently allows you to easily create emulations
of USB devices in Python. Control is fine-grained enough that you can cause all
kinds of USB misbehaviors. :)

For more information, see:

 * [Travis Goodspeed's blog post on FaceDancer](http://travisgoodspeed.blogspot.com/2012/07/emulating-usb-devices-with-python.html)
 * [The FaceDancer 21, a supported board](http://goodfet.sourceforge.net/hardware/facedancer21/)

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
 * RPi + Max3241 Raspdancer boards (```BACKEND=raspdancer```)

Note that hardware restrictions prevent the MAX3420/MAX3421 boards from emulating
more complex devices-- there's limitation on the number/type of endpoints that can be
set up. The LPC4330 boards-- such as the GreatFET-- don't suffer these limitations.

## What boards could be supported soon?
 * Any Linux computer with gadgetfs support (e.g. the Pi Zero or Beaglebone Black)

## What features do you plan on adding?

The roadmap is hazy, but in addition to multi-board support, this repository
eventually will be home to some cool new features, such as:

 * High-speed ("USB 2.0") device emulation on devices with USB 2.0 PHYS
 * [USBProxy](https://github.com/dominicgs/USBProxy)-like USB-packet MITM'ing.
 * Limited USB protocol analysis capabilities

## Whose fault _is_ this?

There are a lot of people to blame for the awesomeness that is this repo,
including:

 * Travis Goodspeed
 * Sergey Bratus
 * Kyle Temkin
 * Dominic Spill
 * Michael Ossmann
 * anyone whose name appears in the git history :)

## Contributions?

... are always welcome. Shoot us a PR!
