#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2019 Kevin Laeufer <laeufer@cs.berkeley.edu>

from server import *

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

mk1 = """
program: main.c
	clang main.c -o program
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
    count.increment()
    count.increment()
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
    std::cout << “x=” << part.x << “; y=” << part.y << std::endl;
reset_particle(&part);
    std::cout << “x=” << part.x << “; y=” << part.y << std::endl;
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
    std::cout << “x=” << part->x << “; y=” << part->y << std::endl;
}
"""

app_dir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))

if __name__ == '__main__':
	address = ("localhost", 12345)
	student_dir = 'students'
	compiler_dir = 'compiler'
	code_mirror = 'codemirror-5.45.0'
	lib_dirs = [os.path.join('ext', code_mirror, dd) for dd in ['lib', 'mode/clike']] + ['style']
	app = App([
		Part(1, name="Program 1", program=p1, makefile=mk1, steps=[
			IntroStep(1, "Intro", "Look at the program. It has a bug. In the following steps we will first form a hypothesis and then try out various debugging techniques in order to find the problem."),
			QuestionStep(2, "What should the program do?",
						 "Please take a moment to read through the source code of the program provided below. What do you think is the program intended to do? Put your thoughts into the text box below.",
						 "What do you think the program output will be?"),
			QuestionStep(3, "What are potential bugs?", "", ""),
			QuestionStep(4, "What would you do to debug?", "", ""),
			RunStep(5, "Run the program", ""),
			ModifyStep(6, "Try Debug Technique 1", ""),
			ModifyStep(7, "Fix Program", ""),
			DoneStep(8, "Done", "Congratulations, you are done! Once you are ready to move on to debug the next program, click 'next'."),
		])


	], student_dir=student_dir, compiler_dir=compiler_dir)
	serv = Server(address=address, app=app, student_dir=student_dir, lib_dirs=lib_dirs, app_dir=app_dir)
	serv.serve_forever()
