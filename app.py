#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2019 Kevin Laeufer <laeufer@cs.berkeley.edu>

from server import *
from typing import List

p1 = """
#include<iostream>

int main(int argc, const char* argv[]) {
    int buffer[10];
    int x;
    for(int ii = 1; ii <= 10; ii += 1) {
        buffer[ii] = ii;
    }
    std::cout << buffer[10] << std::endl;
}
"""

p2 = """
#include<iostream>

struct Counter {
    int* count;
    Counter() {}
    void increment() { *count += 1; }
    int get() { return *count; }
};
int main(int argc, const char* argv[]) {
    Counter count;
    count.increment();
    count.increment();
    std::cout << count.get() << std::endl;
}
"""

p3 = """
#include<iostream>

struct particle_t { int x; int y; };
void reset_particle(particle_t* part_ptr) {
    particle_t part = *part_ptr;
    part = {0, 0};
}
int main(int argc, const char* argv[]) {
	particle_t part = {10, 10};    
	std::cout << "x=" << part.x << "; y=" << part.y << std::endl;
	reset_particle(&part);
	std::cout << "x=" << part.x << "; y=" << part.y << std::endl;
}
"""

p4 = """
#include<iostream>

struct particle_t { int x; int y; };
particle_t* make_particle() {
    particle_t part = { -10, 10 };
    return &part;
}
int main(int argc, const char* argv[]) {
particle_t* part = make_particle();
    std::cout << "x=" << part->x << "; y=" << part->y << std::endl;
}
"""

app_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

def short_demo() -> List[Part]:
	return [Part(1, name="Program 1", program=p1, steps=[
			TextStep(1, "Intro", "Explain idea to student.", False),
			QuestionStep(2, "What should the program do?",
						 "Please take a moment to read through the source code of the program provided below. What do you think is the program intended to do? Put your thoughts into the text box below.",
						 "What do you think the program output will be?"),
			QuestionStep(3, "What are potential bugs?", "", ""),
			RunStep(4, "Try different compilers and flags", "TODO: better guidance"),
			TextStep(5, "Done", "Congratulations, you are done! Once you are ready to move on to debug the next program, click 'next'.", False),
		]),
			Part(2, "Program 2", p2, steps=[RunStep(1, "", "")]),
			Part(3, "Program 3", p3, steps=[RunStep(1, "", "")]),
			Part(4, "Program 4", p4, steps=[RunStep(1, "", ""), DoneStep(2, "Done", "End of the demo.")]),
			]


# src: https://github.com/google/sanitizers/wiki/AddressSanitizerExampleUseAfterFree
use_after_free_program = """
int main(int argc, char **argv) {
  int *array = new int[100];
  delete [] array;
  return array[argc];  // BOOM
}
"""

use_after_return_program = """
int *ptr;
void FunctionThatEscapesLocalObject() {
  int local[100];
  ptr = &local[0];
}

int main(int argc, char **argv) {
  FunctionThatEscapesLocalObject();
  return ptr[argc];
}
"""



"""
Notes
-----

Bug Classes:
* Use After Free (Heap) [address]
* Use After Return (Stack) [address]
* Buffer Overflow (Heap/Stack) [address]

* Bounds Check for static array size [undefined]
* Nullpointer Dereference [undefined]
* Return from non-void function [undefined]

* Uninitialized Pointer [memory]

"""
def complete_unit() -> List[Part]:
	intro = Part(1, "Your Compiler as a Bug Finding Tool", "",[
		TextStep(1, "Introduction",
				  "While developing software in C++ you might have struggled with your program crashing unexpectedly. " +
				  "Once that happens it can be hard to understand what exactly causes it to fail. " +
				  "This interactive online tutorial will help you learn about how your compiler can support you in debugging your programs.", False),
		TextStep(2, "Bug Classes",
				  "Over the course of this tutorial we will teach you how to identify and fix various kinds of bugs:<br/><ul>"+
				  "<li>Use After Free</li>" +
				  "<li>Use After Return</li>" +
				  "<li>Buffer Overflows</li>" + "</ul>", False),
		TextStep(3, "Start", "Once you are ready to get started, click <b>next</b>.",  False)
	])

	bugs = Part(2, "Use After Free", program=use_after_free_program, steps=[
		TextStep(1, "Intro", "lol", True)
	])

	return [intro, bugs]

if __name__ == '__main__':
	address = ("localhost", 12345)
	#student_dir = 'students_demo'
	student_dir = 'students'
	unit = complete_unit()
	compiler_dir = 'compiler'
	code_mirror = 'codemirror-5.45.0'
	lib_dirs = [os.path.join('ext', code_mirror, dd) for dd in ['lib', 'mode/clike']] + ['style']
	app = App(unit,	student_dir=student_dir, compiler_dir=compiler_dir)
	serv = Server(address=address, app=app, student_dir=student_dir, lib_dirs=lib_dirs, app_dir=app_dir)
	serv.serve_forever()
