UVic Schedule Scraper
=====================

Use this program to find schedules for your courses!

While schedulecourses.com is out of commission, I thought I'd help out my fellow students with their
course scheduling needs. This program will find combinations of sections that work together without
conflicts on your timetable, and present you with the CRNs for easy registration when the time comes.

[See it in action here (YouTube link).](https://youtu.be/BdfHxtnDEm8)

[Get started by downloading the program here.](https://github.com/blerchy/schedule-scraper/releases/)

## How to use.

To run the program, you will need to have Python 3 installed. Then,
you'll need to download the `schedule_scraper.py` program to your computer, and install a couple dependencies.

```
$ pip install bs4
...
$ pip install requests
...
$ python schedule_scraper.py
```

From there, you'll be able to run the program simply by calling 

```
$ python schedule_scraper.py
```

on the terminal/powershell from wherever you've downloaded it to. If you do not have Python 3 installed, there is a helpful
guide to doing so [here.](https://realpython.com/installing-python)

The program will then ask you to add some courses. Follow the prompts and happy scheduling!

## Get in touch.

Feel free to get in touch with me if you are having issues, but I cannot promise I'll be able to help.
This was written over the course of three or four bursts of manic typing in the 48 hours following the
posting of schedules on May 31, so there
are bound to be some bugs. I hope to iron those out as they are reported, but unfortunately I am
busy these days so I can't promise speedy fixes.

If you'd like to report any problems, or just drop a line, please email me at [mlebl@uvic.ca](mailto:mlebl@uvic.ca)
You can also post a ticket on this GitHub page if you like.

## Contributions welcome.

Any programmers out there are welcome to improve the program! It is licensed under the GPL, so it is
free software. Feel free to remix and redistribute at your leisure subject to the license. If you make
a great change, please consider opening a pull request!

## No thank you.

If this program isn't working for you for whatever reason, I can suggest another website to help you
put together your schedule: [courseup.vikelabs.dev](http://courseup.vikelabs.dev). I don't have a lot
of experience using it (I didn't even know it existed until I tried to promote this program…) but I've
read great things about it.

## Thanks!

I hope this program proves useful to you.

