#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2019 Kevin Laeufer <laeufer@cs.berkeley.edu>

import os, subprocess, re, tempfile

def ret_to_dict(ret):
	return { 'ret': ret.returncode, 'stdout': ret.stdout.decode('utf8'), 'stderr': ret.stderr.decode('utf-8') }

class Compiler:
	def __init__(self, working_dir):
		self.allowed_flags = [f'-O{ii}' for ii in range(4)] + ['-g', '-Wall', '-fsanitize=address']
		self.working_dir = os.path.abspath(working_dir)
		self.versions = self.test()

	def test(self):
		# ensure working dir exists
		if not os.path.isdir(self.working_dir):
			root_dir = os.path.dirname(self.working_dir)
			assert os.path.isdir(root_dir), f"{root_dir} does not exists"
			os.mkdir(self.working_dir)
		assert os.path.isdir(self.working_dir), f"{self.working_dir} does not exist"

		# ensure compiler is available
		versions = []
		for comp in ['g++', 'clang++']:
			r = self._run(comp, '--version')
			assert r.returncode == 0, f"compiler {comp} not found: {r.stderr}"
			name, version = re.match(r'([a-zA-Z\+\(\) ]+)([\d\.]+)', r.stdout.decode('utf-8')).groups()
			versions.append(version)
		return versions

	def _run(self, compiler, args, cwd=None):
		assert compiler in {'g++', 'clang++'}
		if cwd is None: cwd = self.working_dir
		assert os.path.isdir(cwd)
		if not isinstance(args, list): args = [args]
		cmd = [compiler] + args
		PIPE=subprocess.PIPE
		ret = subprocess.run(cmd, cwd=cwd, stderr=PIPE, stdout=PIPE)
		return ret

	def compile(self, compiler, flags, source, exe):
		assert isinstance(flags, list)
		if compiler not in {'g++', 'clang++'} : return None, None
		for flag in flags:
			if flag not in self.allowed_flags:
				return None, None
		# get working directory
		cwd = tempfile.mkdtemp(prefix=compiler+'_', dir=self.working_dir)
		print(cwd)
		# generate c++ file
		program_cpp = 'program.cpp'
		with open(os.path.join(cwd, program_cpp), 'w') as ff: ff.write(source)
		# create argument list
		args = flags + [program_cpp, '-o', exe]
		# compile program
		r = self._run(compiler, args=args, cwd=cwd)
		if r.returncode == 0:
			assert os.path.isfile(os.path.join(cwd, exe))
		return cwd, ret_to_dict(r)

	def compile_and_run(self, compiler, flags, source):
		#print(f'compile_and_run({compiler}, {flags}, {source})')
		exe = 'program'
		cwd, cc = self.compile(compiler=compiler, flags=flags, source=source, exe=exe)
		if cc is None: return None
		if cc['ret'] != 0:
			return {'compile': cc, 'run': {}}
		# run program
		PIPE = subprocess.PIPE
		cmd = [os.path.join(cwd, exe)]
		ret = subprocess.run(cmd, cwd=cwd, stderr=PIPE, stdout=PIPE)
		return {'compile': cc, 'run': ret_to_dict(ret), 'flags': flags, 'source': source, 'compiler': compiler}
