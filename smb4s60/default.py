import sys
import os.path
import copy
import socket
import e32
import os

sys.path.append(r'e:\projects\smb4s60')

import nmb
import smb



import appuifw
from key_codes import EKeyLeftArrow

class config:
	def __init__(self, config_path=r'E:\.smb4s60\.config'):
		self.config = {}
		self.config_path = config_path
		if os.path.exists(config_path):
			fo = open(config_path)
			self.config = eval(fo.read())
			fo.close()
		else:
			if not os.path.exists(os.path.dirname(config_path)):
				os.makedirs(os.path.dirname(config_path))
	def get_hosts(self):
		if self.config:
			return ['%s@%s' % (host['username'], host['hostname']) for host in self.config['hosts']]
		else:
			return []
	def write_config(self):
		fo = open(self.config_path, 'w')
		fo.write(repr(self.config))
		fo.close()
	def add_host(self, hostname, username=None, password=None):
		if not self.config.has_key('hosts'):
			self.config['hosts'] = []
		for host in self.config['hosts']:
			if host['hostname'] == hostname and host['username'] == username and host['password'] == password:
				return
		self.config['hosts'].append({'hostname': hostname,
									 'username': username,
									 'password': password})
	def del_host(self, hostname):
		found = 0
		if self.config.has_key('hosts'):
			for i in range(len(self.config['hosts'])):
				if self.config['hosts'][i]['hostname'] == hostname:
					found = i
					break;
		del self.config['hosts'][i]

class app:
	path = ['']
	service = ''
	def __init__(self, netbios_hostname=None):
		#appuifw.app.screen = 'large'
		self.password = None
		self.username = None
		self.debug = False
		self.error_retry = 0
		self.config = config()
		self.set_title()
		self.apn = socket.select_access_point()
		self.dest_name=netbios_hostname
		self.set_host(netbios_hostname)
		#self.connect()
		self.set_menus()
		self.download_textinfo = appuifw.Text()
		self.download_textinfo.style = appuifw.STYLE_BOLD
	def set_title(self, text=''):
		if text:
			text = ' - ' + text
		appuifw.app.title = unicode('SMB4S60' + text)
	def show_options(self, options, required=True):
		options = [unicode(opt) for opt in options]
		selected = appuifw.selection_list(options, search_field=1)		
		if selected == None and required:
			self.error('Host is required')
			selected = self.show_options(options)
		return selected
	def set_host(self, host=None):
		print self.config.get_hosts()
		hosts = self.config.get_hosts() + ['New host ...']
		if hosts:
			option = self.show_options(hosts)
			print 'Option selected: ' + str(option)
			if hosts[-1] != hosts[option]:
				username = self.config.config['hosts'][option]['username']
				password = self.config.config['hosts'][option]['password']
				host = hosts[option].split('@')[1].encode('utf-8')		
				self.username = username
				self.password = password
		if not host:
			host = appuifw.query(u'Enter hostname', 'text', u'simpleshare').encode('utf-8')
			if not host:
				appuifw.note(u'Please type a hostname to browse', 'info')
				host = self.set_host()
		self.dest_name = host
		self.connect()
		self.set_title(self.dest_name)
		self.flist = self.get_shares()
		self.lbox = appuifw.Listbox(self.flist, self.selector)
		appuifw.app.body = self.lbox
	def get_text(self, text, error, required=True, type='text'):
		s = appuifw.query(unicode(text), type)
		if required and not s:
			appuifw.info(unicode(error), 'error')
			s = self.get_text(text, error, required)
		return s
	def get_pass(self, text, error, required=True):
		return self.get_text(text, error, required, 'code')
	def remote_chdir(self, get_path=True):
		if get_path:
			path = self.get_text('Enter the path', 'Path is required')
			try: 
				self.remote.check_dir(self.service, path, self.password)
				self.path = path.split('\\')
			except smb.SessionError:
				self.error(path + 'is not valid')
				return
		self.flist = self.get_filelist()
		self.lbox.set_list([unicode(f.get_longname()) for f in self.flist])		
	def set_menus(self):
		appuifw.app.menu = [(u'Change Host ...', self.set_host), 
							(u'Change Directory ...', self.remote_chdir)]
	def dprint(self, info):
		if self.debug:
			print info
	def connect(self):
		if self.error_retry > 3:
			self.apn = socket.select_access_point()
		try:
			del self.netbios
			del self.addrs
			del self.remote
		except:
			pass
		self.netbios = nmb.NetBIOS(apn=self.apn)
		self.dprint(5)
		addrs = self.netbios.gethostbyname(self.dest_name)
		self.dprint(6)
		self.remote = smb.SMB(self.dest_name, addrs[0].get_ip())		
		if self.remote.is_login_required():
			if not self.username:
				self.username = self.get_text('Enter Username:', 'Username is required').encode('utf-8')
			if not self.password:
				self.password = self.get_pass('Enter Password:', 'Password is required').encode('utf-8')
			self.remote.login(self.username, self.password)
		self.config.add_host(self.dest_name, self.username, self.password)
		self.config.write_config()
		self.dprint(7)
	def get_unit(self, number, counter=0):
		units = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB']
		if number > 1023.0 and counter < 5:
			number = number / 1024.0
			return self.get_unit(number, counter + 1)
		return "%s %s" % (round(number, 2), units[counter])
	def list_shares(self):
		try:
			shares = self.remote.list_shared()
			self.error_retry = 0
			self.error_retry = 0
			return shares
		except socket.error:
			self.error_retry += 1
			self.connect()
			return self.remote.list_shared()
	def list_path(self, *args, **kws):
		try:
			kws['password'] = self.password
			paths = self.remote.list_path(*args, **kws)
			self.error_retry = 0
			return paths
		except socket.error:
			self.error_retry += 1
			self.connect()
			return self.remote.list_path(*args, **kws)
	def get_shares(self):
		self.shares = self.list_shares()
		share_list = [unicode(s.get_name()) for s in self.shares if s.get_type() == 0]
		return share_list
	def compare_string(self, s1, s2):
		if s1.get_longname() > s2.get_longname():
			return 1
		elif s1 == s2:
			return 0
		else:
			return -1
	def get_filelist(self):
		folder_list = [f for f in self.list_path(self.service, os.path.join(*self.path) + '\\*') if f.get_longname() != '.']
		folders = [f for f in folder_list if f.is_directory()]
		folders.sort(self.compare_string)
		files = [f for f in folder_list if not f.is_directory()]
		files.sort(self.compare_string)
		folder_list = folders + files
		return folder_list
	def undo(self):
		self.service = copy.copy(self.oldservice)
		self.path = copy.copy(self.oldpath)
	def writer(self, data):
		e32.reset_inactivity()
		self.size += len(data)
		self.fh.write(data)
		self.download_textinfo.set(unicode(self.get_unit(self.size) + " of " + self.get_unit(self.selected_fsize) + " downloaded\n" + "(%.2f %%)" % (self.size / float(self.selected_fsize) * 100.0)))
	def error(self, errormsg):
		appuifw.note(unicode(errormsg), 'error')
	def selector(self, index=None):
		self.dprint('Entering selector')
		self.oldservice = copy.copy(self.service)
		self.dprint('after copy.copy(self.service)')
		self.oldpath = copy.copy(self.path)
		self.dprint('after copy.copy(self.path)')
		show_shares = False
		selected = self.lbox.current()
		if self.service == '':
			self.service = self.flist[selected].encode('utf-8')
			self.path = ['']
		else:
			if not self.flist[selected].is_directory():
			    #It is a file which has been selected by user
				selected_file = self.flist[selected].get_longname()
				self.selected_fsize = self.flist[selected].get_filesize() 
				self.size = 0
				path = appuifw.query(u'Specify destination path:', 'text', u'e:\\downloads\\')
				if os.path.exists(path):
					if os.path.isdir(path):
						fname = os.path.join(path, selected_file)
					else:
						self.error(u'Not a directory')
						return
				else:
					try:
						os.makedirs(path)
						fname = os.path.join(path, selected_file)
					except:
						self.error(u'Unable to create directory')
						return
				self.fh = open(fname, 'wb')		
				appuifw.app.body = self.download_textinfo
				self.download_textinfo.set(u'Please wait for the download to complete')
				try:
					self.remote.retr_file(self.service, os.path.join(*self.path) + '\\' + self.flist[selected].get_longname(), self.writer, password=self.password)
				finally:
					self.fh.close()
				self.download_textinfo.set(unicode(os.path.join(*self.path) + '\\' + self.flist[selected].get_longname() + 'download completed'))
				e32.ao_sleep(1)
				appuifw.app.body = self.lbox
				#appuifw.Content_handler().open_standalone(unicode('e:\\' + selected_file))
			elif self.flist[selected].get_longname().encode('utf-8') == '..':
				if len(self.path) > 0 and self.path != ['']:
					self.path.pop()
				else:
					show_shares = True
					self.path = ['']
			else:
			    self.path.append(self.flist[selected].get_longname().encode('utf-8'))
		try:
			if show_shares:
				share_list = self.get_shares()
				self.lbox.set_list(share_list)
				self.flist = share_list
				self.service = ''
			else:
				self.remote_chdir(get_path=False)
		except Exception, e:
			self.undo()
			self.error(u'Unable to Access: ' + unicode(str(e)))

		
	
#a = app('simpleshare')
def get_host():
	host = appuifw.query(u'Enter hostname', 'text', u'simpleshare').encode('utf-8')
	if not host:
		appuifw.note(u'Please type a hostname to browse', 'info')
		host = get_host()
	return host
	

	
#host = get_host()
a = app()
lck = e32.Ao_lock()
lck.wait()
