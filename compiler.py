#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2019 Kevin Laeufer <laeufer@cs.berkeley.edu>

import os, subprocess, re, tempfile

def ret_to_dict(ret):
	return { 'ret': ret.returncode, 'stdout': ret.stdout.decode('utf8'), 'stderr': ret.stderr.decode('utf-8') }

class Compiler:
	@staticmethod
	def gcc(working_dir):
		flags = ['-O0']
		return Compiler(binary='g++', allowed_flags=flags, working_dir=working_dir)

	@staticmethod
	def clang(working_dir):
		flags = ['-O0']
		return Compiler(binary='clang++', allowed_flags=flags, working_dir=working_dir)


	def __init__(self, binary, allowed_flags, working_dir):
		self.binary = binary
		self.allowed_flags = allowed_flags
		self.working_dir = os.path.abspath(working_dir)
		self.version = self.test()

	def test(self):
		# ensure working dir exists
		if not os.path.isdir(self.working_dir):
			root_dir = os.path.dirname(self.working_dir)
			assert os.path.isdir(root_dir), f"{root_dir} does not exists"
			os.mkdir(self.working_dir)
		assert os.path.isdir(self.working_dir), f"{self.working_dir} does not exist"

		# ensure compiler is available
		r = self._run('--version')
		assert r.returncode == 0, f"compiler {self.binary} not found: {r.stderr}"
		name, version = re.match(r'([a-zA-Z\(\) ]+)([\d\.]+)', r.stdout.decode('utf-8')).groups()
		return version

	def _run(self, args, cwd=None):
		if cwd is None: cwd = self.working_dir
		assert os.path.isdir(cwd)
		if not isinstance(args, list): args = [args]
		cmd = [self.binary] + args
		PIPE=subprocess.PIPE
		ret = subprocess.run(cmd, cwd=cwd, stderr=PIPE, stdout=PIPE)
		return ret

	def compile(self, flags, source, exe):
		assert isinstance(flags, list)
		for flag in flags:
			if flag not in self.allowed_flags:
				return {}
		# get working directory
		cwd = tempfile.mkdtemp(prefix=self.binary+'_', dir=self.working_dir)
		# generate c++ file
		program_cpp = 'program.cpp'
		with open(os.path.join(cwd, program_cpp), 'w') as ff: ff.write(source)
		# create argument list
		args = flags + [program_cpp, '-o', exe]
		# compile program
		r = self._run(args=args, cwd=cwd)
		if r.returncode == 0:
			assert os.path.isfile(os.path.join(cwd, exe))
		return cwd, ret_to_dict(r)

	def compile_and_run(self, flags, source):
		exe = 'program'
		cwd, cc = self.compile(flags=flags, source=source, exe=exe)
		if cc['ret'] != 0:
			return {'compile': cc, 'run': {}}
		# run program
		PIPE = subprocess.PIPE
		cmd = [os.path.join(cwd, exe)]
		ret = subprocess.run(cmd, cwd=cwd, stderr=PIPE, stdout=PIPE)
		return {'compile': cc, 'run': ret_to_dict(ret), 'flags': flags, 'source': source}
