# firstproject
Solar data compiler

The code here is from my first real Python program, written in the summer of 2015 and refactored (into python3, phew) in 2019.

The program runs on a raspberry pi connected to a network where a certain solar panel system is running and publishing an html page every so often.
As it does so, the python program scrapes the page for data such as the total power generated and reports it to a Google Sheet.

Why a Google Sheet and not a reasonable database, you might ask?

Two reasons. First, familiarity at the time, and second, for easy data processing and demonstration.

Some of the code structure and practices are a little rough, but they are mostly in the same general format they were written in originally.
