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

use_after_free_intro = """
In C and C++ the programmer is responsible for allocating and deallocating memory on the heap.
Once memory has been deallocated using <b>free</b> or <b>delete</b>, it can no longer be used.
However, a failure to follow these rules won't be caught by the compiler which will happily compile the code
shown bellow.<br/>
"""
# However, the bug can be automatically detected when the program is run using a <b>sanitizer</b>.

# src: https://github.com/google/sanitizers/wiki/AddressSanitizerExampleStackOutOfBounds
stack_buffer_overflow_program = """
int main(int argc, char **argv) {
  int stack_array[100];
  stack_array[1] = 0;
  return stack_array[argc + 100];  // BOOM
}
"""

buffer_overflow_intro = """
In C and C++ you are able to deal with a sequence of elements of the same type using arrays.
Arrays can be allocated using <b>malloc</b>, <b>new []</b> or statically/on the stack using the <b>T name[LEN]</b> pattern.<br/>
Whether they are statically or dynamically allocated, arrays always have a specific size and when indexing into an array,
the index must be >= 0 and < than the length of the array.
However, for performance reasons, that restriction is not enforced by the compiler. Instead your code has to make sure
to index into arrays correctly.<br/>
When your code indexes beyond the array, it could crash, data could be silently corrupted or nothing might happen.
Thus these errors are hard to debug. Fortunately your compiler can help you automatically find those bugs.

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

def bug_part(id: int, name: str, program: str, intro: str) -> Part:
	name_i = f"<i>{name}</i>"
	return Part(id, name, program=program, steps=[
		TextStep(1, "", intro, True),
		QuestionStep(2, "", f"""
				Take a minute to try and understand the program.<br/>
				While the {name_i} error is easy to spot in this small example program,
				there is no compiler that will warn you (during compile time) about {name_i} errors as they are impossible
				to detect in the general case.<br/>
				What do you think might be the reason for this?
				
		""", f"Why are {name} bugs impossible for the compiler to detect?"),
		RunStep(3, "", """
		Now you can compile and run the program using the <b>Compile &amp; Run</b> button below.<br/>
		Take a minute to try out different compilers and compiler flags and observe the results.<br/>
		Are you able to detect the bug automatically?
 		"""),
		QuestionStep(4, "", f"""
		Please summarize your findings.<br/>
		Which compiler flags worked in order to detect the {name_i} bug?<br/>
		When was it detected? During compilation or during execution?<br/>
		Were there any differences between the different compilers?
		""", "Please summarize your findings:")
	])

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


	# Try to come up with an explanation of why the compiler cannot detect bugs like this in the general case.
	bugs = [bug_part(2, "Use After Free", use_after_free_program, use_after_free_intro),
			bug_part(3, "Buffer Overflow", stack_buffer_overflow_program, buffer_overflow_intro)]

	return [intro]+bugs

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
