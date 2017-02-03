__kupfer_name__ = _("File Actions")
__kupfer_sources__ = ()
__kupfer_text_sources__ = ()
__kupfer_actions__ = (
		"MoveTo",
		"Rename",
		"CopyTo",
	)
__description__ = _("More file actions")
__version__ = ""
__author__ = "Ulrik"

import gio
import os
# since "path" is a very generic name, you often forget..
from os import path as os_path

from kupfer.objects import Action, FileLeaf, TextLeaf, TextSource
from kupfer.objects import OperationError
from kupfer import pretty


def _good_destination(dpath, spath):
	"""If directory path @dpath is a valid destination for file @spath
	to be copied or moved to.
	"""
	if not os_path.isdir(dpath):
		return False
	spath = os_path.normpath(spath)
	dpath = os_path.normpath(dpath)
	if not os.access(dpath, os.R_OK | os.W_OK | os.X_OK):
		return False
	cpfx = os_path.commonprefix((spath, dpath))
	if os_path.samefile(dpath, spath) or cpfx == spath:
		return False
	return True

class MoveTo (Action, pretty.OutputMixin):
	def __init__(self):
		Action.__init__(self, _("Move To..."))
	def has_result(self):
		return True
	def activate(self, leaf, obj):
		sfile = gio.File(leaf.object)
		bname = sfile.get_basename()
		dfile = gio.File(os_path.join(obj.object, bname))
		try:
			ret = sfile.move(dfile, flags=gio.FILE_COPY_ALL_METADATA)
			self.output_debug("Move %s to %s (ret: %s)" % (sfile, dfile, ret))
		except gio.Error as exc:
			raise OperationError(str(exc))
		else:
			return FileLeaf(dfile.get_path())

	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)
	def requires_object(self):
		return True

	def item_types(self):
		yield FileLeaf
	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item):
		return _good_destination(obj.object, for_item.object)
	def get_description(self):
		return _("Move file to new location")
	def get_icon_name(self):
		return "go-next"

class RenameSource (TextSource):
	"""A source for new names for a file;
	here we "autopropose" the source file's extension,
	but allow overriding it as well as renaming to without
	extension (either using a terminating space, or selecting the
	normal TextSource-returned string).
	"""
	def __init__(self, sourcefile):
		self.sourcefile = sourcefile
		name = _("Rename To...").rstrip(".")
		TextSource.__init__(self, name)

	def get_rank(self):
		# this should rank high
		return 100

	def get_items(self, text):
		if not text:
			return
		basename = os_path.basename(self.sourcefile.object)
		root, ext = os_path.splitext(basename)
		t_root, t_ext = os_path.splitext(text)
		if text.endswith(" "):
			yield TextLeaf(text.rstrip())
		else:
			yield TextLeaf(text) if t_ext else TextLeaf(t_root + ext)

	def get_gicon(self):
		return self.sourcefile.get_gicon()

class Rename (Action, pretty.OutputMixin):
	def __init__(self):
		Action.__init__(self, _("Rename To..."))

	def has_result(self):
		return True
	def activate(self, leaf, obj):
		sfile = gio.File(leaf.object)
		dest = os_path.join(os_path.dirname(leaf.object), obj.object)
		dfile = gio.File(dest)
		try:
			ret = sfile.move(dfile)
			self.output_debug("Move %s to %s (ret: %s)" % (sfile, dfile, ret))
		except gio.Error as exc:
			raise OperationError(str(exc))
		else:
			return FileLeaf(dfile.get_path())

	def activate_multiple(self, objs, iobjs):
		raise NotImplementedError

	def item_types(self):
		yield FileLeaf
	def valid_for_item(self, item):
		return os.access(item.object, os.R_OK | os.W_OK)

	def requires_object(self):
		return True
	def object_types(self):
		yield TextLeaf

	def valid_object(self, obj, for_item):
		dest = os_path.join(os_path.dirname(for_item.object), obj.object)
		return os_path.exists(os_path.dirname(dest)) and \
				not os_path.exists(dest)

	def object_source(self, for_item):
		return RenameSource(for_item)

	def get_description(self):
		return None

class CopyTo (Action, pretty.OutputMixin):
	def __init__(self):
		Action.__init__(self, _("Copy To..."))

	def has_result(self):
		return True

	def _finish_callback(self, gfile, result, data):
		self.output_debug("Finished copying", gfile)
		dfile, ctx = data
		try:
			gfile.copy_finish(result)
		except gio.Error:
			ctx.register_late_error()
		else:
			ctx.register_late_result(FileLeaf(dfile.get_path()))

	def wants_context(self):
		return True

	def activate(self, leaf, iobj, ctx):
		sfile = gio.File(leaf.object)
		dpath = os_path.join(iobj.object, os_path.basename(leaf.object))
		dfile = gio.File(dpath)
		try:
			ret = sfile.copy_async(dfile, self._finish_callback,
					user_data=(dfile, ctx),
					flags=gio.FILE_COPY_ALL_METADATA)
			self.output_debug("Copy %s to %s (ret: %s)" % (sfile, dfile, ret))
		except gio.Error as exc:
			raise OperationError(str(exc))

	def item_types(self):
		yield FileLeaf
	def valid_for_item(self, item):
		return (not item.is_dir()) and os.access(item.object, os.R_OK)
	def requires_object(self):
		return True
	def object_types(self):
		yield FileLeaf
	def valid_object(self, obj, for_item):
		return _good_destination(obj.object, for_item.object)
	def get_description(self):
		return _("Copy file to a chosen location")
