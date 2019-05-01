#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2019 Kevin Laeufer <laeufer@cs.berkeley.edu>

import json, os, sys, urllib
import http.server
from urllib.parse import urlparse
from typing import List, Optional
from functools import reduce, total_ordering
import operator
from jinja2 import Template
from compiler import Compiler
from ansi2html import Ansi2HTMLConverter

def assert_uids(items):
	uids = {s.uid for s in items}
	assert len(uids) == len(items), "non unique id!"


class Step:
	def __init__(self, uid: int, name: str, instructions: str):
		self.uid = f'step{uid}'
		self.name = name
		self.instructions = instructions

	def to_dict(self) -> dict:
		name = self.__class__.__name__
		assert name.endswith('Step')
		kind = name[:-4]
		return {'uid': self.uid, 'instructions': self.instructions, 'name': self.name, 'kind': kind}

class IntroStep(Step):
	def __init__(self, uid: int, name: str, instructions: str):
		super().__init__(uid=uid, name=name, instructions=instructions)

class DoneStep(Step):
	def __init__(self, uid: int, name: str, instructions: str):
		super().__init__(uid=uid, name=name, instructions=instructions)

class QuestionStep(Step):
	def __init__(self, uid: int, name: str, instructions: str, question: str):
		super().__init__(uid=uid, name=name, instructions=instructions)
		self.question = question
		self.answers = {}

	def to_dict(self) -> dict:
		dd = super().to_dict()
		dd['question'] = self.question
		dd['answers'] = self.answers
		return dd

class RunStep(Step):
	def __init__(self, uid: int, name: str, instructions: str):
		super().__init__(uid=uid, name=name, instructions=instructions)

class ModifyStep(Step):
	def __init__(self, uid: int, name: str, instructions: str):
		super().__init__(uid=uid, name=name, instructions=instructions)


class Part:
	def __init__(self, uid: int, name: str, program: str, makefile: str, steps: List[Step]):
		assert_uids(steps)
		self.uid = f'program{uid}'
		self.name = name
		self.program = program
		self.makefile = makefile

		self.step_to_pos = {s: ii for ii, s in enumerate(steps)}
		self.pos_to_step = steps
		self.step_count = len(steps)
		self.steps = {s.uid: s for s in steps}

	def to_dict(self) -> dict:
		return {'uid': self.uid, 'name': self.name, 'program': self.program, 'makefile': self.makefile,
				'steps': [(s.name, s.uid) for s in self.steps.values()] }

	def next_step(self, step):
		next_pos = self.step_to_pos.get(step, self.step_count - 1) + 1
		if next_pos >= self.step_count: return None
		return self.pos_to_step[next_pos]

def load_step_specific_data(data):
	return {tuple(entry[0]): entry[1] for entry in data}
def save_step_specific_data(data):
	return [(key,value) for key,value in data.items()]

class Student:
	def __init__(self, uid, progress, answers, runs):
		assert isinstance(progress, int)
		self.uid = uid
		self.progress = progress
		self.answers = answers
		self.runs = runs
	@staticmethod
	def load(filename: str, start):
		assert filename.endswith('.json')
		expected_uid = os.path.basename(filename)[:-len('.json')]
		with open(filename) as ff:
			dd = json.load(ff)
		assert dd['uid'] == expected_uid, f"{dd['uid']} != {expected_uid}"
		if dd['progress'] is None: dd['progress'] = start
		dd['answers'] = load_step_specific_data(dd.get('answers', []))
		dd['runs'] = load_step_specific_data(dd.get('runs', []))
		return Student(**dd)
	def save(self, student_dir: str):
		assert os.path.isdir(student_dir)
		filename = os.path.join(student_dir, self.uid + ".json")
		answers = save_step_specific_data(self.answers)
		runs = save_step_specific_data(self.runs)
		dd = {'uid': self.uid, 'progress': self.progress, 'answers': answers, 'runs': runs}
		with open(filename, 'w') as ff:
			json.dump(dd, ff, indent=2)

class Error:
	def __init__(self, msg):
		self.msg = msg
	def __str__(self):
		return f"Error({self.msg})"
class Success:
	def __init__(self, dat):
		self.dat = dat
	def __str__(self):
		return f"Success({self.dat})"
class Redirect:
	def __init__(self, path):
		self.path = path
	def __str__(self):
		return f"Redirect({self.path})"

def is_error(e): return isinstance(e, Error)
def is_redirect(e): return isinstance(e, Redirect)

@total_ordering
class PathId:
	def __init__(self, part, step, app):
		assert isinstance(part, str)
		assert isinstance(step, str)
		assert isinstance(app, App)
		self.part = part
		self.step = step
		self.progress = app.uid_progress[(self.part, self.step)]
	def __eq__(self, other):
		assert isinstance(other, PathId)
		return self.progress == other.progress
	def __ne__(self, other):
		return not(self == other)
	def __lt__(self, other):
		assert isinstance(other, PathId)
		return self.progress < other.progress

def selected_flags(rr):
	if rr is None:
		flags = ['-O3']
		compiler = 'g++'
	else:
		flags = rr['flags']
		compiler = rr['compiler']
	dd = {compiler: 'selected=""'}
	#print(flags)
	for flag in flags:
		dd[flag] = 'selected=""' if flag.startswith('-O') else 'checked=""'
	#print(dd)
	return dd

class App:
	def __init__(self, parts: List[Part], student_dir, compiler_dir):
		assert_uids(parts)
		self.parts = {p.uid: p for p in parts}
		self.students = {}
		# make uids comparable
		uids = reduce(operator.add, ([(p.uid, s.uid) for s in p.steps.values()] for p in parts))
		self.start = uids[0]
		self.uid_progress = {uid: ii for ii, uid in enumerate(uids)}
		print(self.uid_progress)
		self.app_html: Optional[Template] = None
		# command list
		self.cmds = {'next': self.next, 'answer': self.answer, 'run': self.run}
		# student directory
		assert os.path.isdir(student_dir)
		self.student_dir = student_dir
		# compiler
		self.comp = Compiler(working_dir=compiler_dir)
		# converter
		self.conv = Ansi2HTMLConverter()

	# load

	def load_assets(self, app_html):
		assert self.app_html is None
		with open(app_html) as ff:
			self.app_html = Template(ff.read())

	def load_students(self, student_dir):
		assert os.path.isdir(student_dir)
		assert len(self.students) == 0, "cannot load students twice!"
		_, _, files = next(os.walk(student_dir))
		for filename in files:
			if filename.endswith('.json'):
				stud = Student.load(os.path.join(student_dir, filename), self.start)
				self.students[stud.uid] = stud
				for (part, step), answer in stud.answers.items():
					self.parts[part].steps[step].answers[stud.uid] = answer

	# run

	def parse_student_path(self, student_id, path):
		if len(path) == 0:
			path = self.start
		if student_id not in self.students: return Error("unknown student")
		if len(path) != 2: return Error("path needs to be (part, step)")
		try:
			part = str(path[0])
			step = str(path[1])
		except ValueError:
			return Error(f"invalid path {path}")
		if part not in self.parts: return Error(f"unknown part: {part}")
		if step not in self.parts[part].steps: return Error(f"unknown step {step} for part {part}")
		path_id = PathId(part=part, step=step, app=self)
		student = self.students[student_id]
		if student.progress < path_id.progress: return Error("student is not at this step yet")
		part = self.parts[path_id.part]
		step = part.steps[path_id.step]
		return Success((student, part, step))

	def ret2html(self, ret):
		if len(ret) == 0: return ret
		#print(f"ret2html({ret})")
		def escape(out):
			return self.conv.convert(out, full=False)
		return {
			'ret': ret['ret'],
			'stdout': escape(ret['stdout']),
			'stderr': escape(ret['stderr']),
		}

	def run2html(self, run):
		rr = dict(run)
		rr['compile'] = self.ret2html(run['compile'])
		rr['run'] = self.ret2html(run['run'])
		return rr


	def view(self, student_id, path_list):
		ret = self.parse_student_path(student_id, path_list)
		if is_error(ret): return ret
		else: student, part, step = ret.dat
		rr = student.runs.get((part.uid, step.uid), None)
		dd = {'student_id': student_id,
			  'part': part.to_dict(),
			  'step': step.to_dict(),
			  'run': self.run2html(rr),
			  'flags': selected_flags(rr),
			  'version': self.comp.versions,
			  }
		return Success(self.app_html.render(dd))

	def exec(self, cmd, student_id, path_list, content):
		ret = self.parse_student_path(student_id, path_list)
		if is_error(ret): return ret
		if cmd not in self.cmds: return Error(f"unknown command: {cmd}")
		return self.cmds[cmd](*ret.dat, content)

	def run(self, student, part, step, content):
		can_run = isinstance(step, RunStep) or isinstance(step, ModifyStep)
		if not can_run: return Error("cannot run in this step")
		if isinstance(step, RunStep): main_src = part.program
		else:                         main_src = content['code'][0]
		compiler = content['compiler'][0]
		flags = [content[f'flag{ii}'][0] for ii in range(10) if f'flag{ii}' in content]
		rr = self.comp.compile_and_run(compiler=compiler, flags=flags, source=main_src)
		rr.update({'flags': flags, 'source': main_src, 'compiler': compiler})
		if rr is None: return Error(f'Invalid compile and run command: {content}')
		step_id = (part.uid, step.uid)
		student.runs[step_id] = rr
		student.save(self.student_dir)
		return Redirect('/'.join(['', student.uid, part.uid, step.uid]))

	def next(self, student, part, step, content):
		# find next step and update student progress
		next_step = part.next_step(step)
		if next_step is None:
			return Error("Done. TODO: implement done state")
		student.progress = self.uid_progress[(part.uid, next_step.uid)]
		return Redirect('/'.join(['', student.uid, part.uid, next_step.uid]))


	def answer(self, student, part, step, content):
		if not isinstance(step, QuestionStep): return Error("Wrong step type! Cannot accept an answer.")
		text = content['answer'][0]
		step_id = (part.uid, step.uid)
		student.answers[step_id] = text
		student.save(self.student_dir)
		step.answers[student.uid] = text
		return Redirect('/'.join(['', student.uid, part.uid, step.uid]))

class Handler(http.server.BaseHTTPRequestHandler):
	def handle_GET(self, app, pp):
		# get requests are only used for loading views and static content
		if len(pp) == 1 and pp[0] in app.students:
			# if only the student id is given -> redirect to first view
			return Redirect('/'.join([pp[0]] + list(app.start)))
		if len(pp) == 3 and pp[0] in app.students:
			# show view
			student_id, p0, p1 = pp
			return app.view(student_id, (p0, p1))
		# static
		pdir = os.path.dirname(self.path)
		for suffix, lib_dir in self.server.lib_dirs.items():
			if pdir.endswith(suffix):
				filename = os.path.join(lib_dir, os.path.basename(self.path))
				with open(filename) as ff:
					return Success(ff.read())
		return Error(f"unknown path: {self.path}")

	def handle_POST(self, app, pp, content):
		if len(pp) != 4:
			return Error(f'Invalid POST path: {pp}')
		return app.exec(cmd=pp[3], student_id=pp[0], path_list=(pp[1],pp[2]), content=content)

	def do_GET(self):
		resp = self.handle_GET(app=self.server.app, pp=self.path.split('/')[1:])
		return self.do_response(resp)

	def parse_POST(self):
		if not 'Content-Length' in self.headers:
			return Error("No Content Length")
		try:
			length = int(self.headers['Content-Length'])
			if length == 0:
				content = {}
			else:
				raw_content = self.rfile.read(length).decode('utf-8')
				try:
					content = json.loads(raw_content)
				except json.JSONDecodeError:
					content = urllib.parse.parse_qs(raw_content)
					#print(raw_content)
					#content = {a:b for a,b in (line.split(" ") for line in raw_content.split('\n') if len(line) > 1)}
		except Exception as ee:
			return Error(str(ee))
		#print("POST", content)
		return self.handle_POST(app=self.server.app, pp=self.path.split('/')[1:], content=content)

	def do_POST(self):
		resp = self.parse_POST()
		return self.do_response(resp)

	def do_response(self, resp):
		if isinstance(resp, Error):
			print(resp)
			self.do_404()
		elif isinstance(resp, Success):
			self.do_200(resp.dat)
		elif isinstance(resp, Redirect):
			print(resp)
			self.do_303(resp.path)
		else:
			assert False, f"Invalid response: {resp}"

	def do_404(self):
		self.send_response(404)
		self.end_headers()
		self.wfile.write(self.server.html_404)

	def do_200(self, response):
		assert isinstance(response, str), response
		self.send_response(200)
		self.end_headers()
		self.wfile.write(response.encode('utf8'))

	def do_303(self, url):
		self.send_response(303, 'See Other')
		self.send_header('Location', url)
		self.end_headers()
		self.wfile.write(self.server.html_303)



class Server(http.server.ThreadingHTTPServer):
	def __init__(self, address, app, student_dir, lib_dirs, app_dir):
		assert isinstance(app, App)
		assert os.path.isdir(app_dir)
		assert all(os.path.isdir(os.path.join(app_dir, dd)) for dd in lib_dirs)
		self.app = app
		self.app.load_assets(app_html=os.path.join(app_dir, 'app.html'))
		self.app.load_students(student_dir=os.path.join(app_dir, student_dir))
		self.lib_dirs = {dd: os.path.join(app_dir, dd) for dd in lib_dirs}
		with open(os.path.join(app_dir, '404.html')) as ff:
			self.html_404 = ff.read().encode('utf8')
		with open(os.path.join(app_dir, '303.html')) as ff:
			self.html_303 = ff.read().encode('utf8')

		super().__init__(address, Handler)

