import sys
import os.path
import copy
import socket
import e32
import os

sys.path.append(r'e:\projects\smb for s60')

import nmb
import smb



import appuifw
from key_codes import EKeyLeftArrow

class app:
	path = ['']
	service = ''
	def __init__(self, netbios_hostname):
		#appuifw.app.screen = 'large'
		self.debug = False
		self.error_retry = 0
		self.dest_name=netbios_hostname
		self.apn = socket.select_access_point()
		self.dprint(1)
		self.connect()
		self.dprint(2)
		self.shares = self.remote.list_shared()
		self.dprint(3)
		appuifw.app.title = u'smb4s60'
		self.flist = self.get_shares()
		self.lbox = appuifw.Listbox(self.flist, self.selector)
		appuifw.app.body = self.lbox
		self.dprint(4)
		self.download_textinfo = appuifw.Text()
		self.download_textinfo.style = appuifw.STYLE_BOLD
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
			return shares
		except socket.error:
			self.error_retry += 1
			self.connect()
			return self.remote.list_shared()
	def list_path(self, *args, **kws):
		try:
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
		if s1 > s2:
			return 1
		elif s1 == s2:
			return 0
		else:
			return -1
	def get_filelist(self):
		folder_list = [f for f in self.list_path(self.service, os.path.join(*self.path) + '\\*') if f.get_longname() != '.']
		folders = [f for f in folder_list if f.is_directory()]
		folders.sort(cmp=self.compare_string)
		files = [f for f in folder_list if not f.is_directory()]
		files.sort(cmp=self.compare_string)
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
		self.oldservice = copy.copy(self.service)
		self.oldpath = copy.copy(self.path)
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
					self.remote.retr_file(self.service, os.path.join(*self.path) + '\\' + self.flist[selected].get_longname(), self.writer)
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
		#print self.path, self.oldpath, self.service, os.path.join(*self.path) + '\\*', 'show_shares: ', show_shares
		try:
			if show_shares:
				share_list = self.get_shares()
				self.lbox.set_list(share_list)
				self.flist = share_list
				self.service = ''
			else:
				self.flist = self.get_filelist()
				self.lbox.set_list([unicode(f.get_longname()) for f in self.flist])
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
	

	
host = get_host()
a = app(host)
lck = e32.Ao_lock()
lck.wait()
#a = app('prempc')
