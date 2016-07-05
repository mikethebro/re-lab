# Copyright (C) 2013 David Tardon (dtardon@redhat.com)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 3 or later of the GNU General Public
# License as published by the Free Software Foundation.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301
# USA
#

import zlib

import bmi
from utils import add_iter, add_pgiter, rdata, key2txt, d2hex, d2bin, bflag2txt, ms_charsets

def ref2txt(value):
	if value == 0xffffffff:
		return 'none'
	else:
		return '0x%x' % value

def update_pgiter_type(page, ftype, stype, iter1):
	page.model.set_value(iter1, 1, (ftype, stype))

zmf2_objects = {
	# gap
	0x3: 'Page',
	0x4: 'Layer',
	# gap
	0x8: 'Rectangle',
	0x9: 'Image',
	0xa: 'Color',
	# gap
	0xc: 'Fill',
	# gap
	0xe: 'Polyline',
	# gap
	0x10: 'Ellipse',
	0x11: 'Star',
	0x12: 'Polygon',
	0x13: 'Text frame',
	0x14: 'Table',
	# gap
	0x16: 'Pen',
	# gap
	0x18: 'Shadow',
	# gap
	0x1e: 'Group',
	# gap
	0x100: 'Color palette',
	# gap
	0x201: 'Bitmap definition',
}

# defined later
zmf2_handlers = {}

class ZMF2Parser(object):

	def __init__(self, data, page, parent, parser):
		self.data = data
		self.page = page
		self.parent = parent
		self.parser = parser

	def parse(self):
		if len(self.data) >= 4:
			(length, off) = rdata(self.data, 0, '<I')
			if length <= len(self.data):
				try:
					self._parse_file(self.data[0:length], self.parent)
				except:
					pass

	def parse_bitmap_db_doc(self, data, parent):
		off = 4
		i = 1
		while off < len(data):
			off = self._parse_object(data, off, parent, 'Bitmap %d' % i)
			i += 1

	def parse_bitmap_def(self, data, parent):
		add_pgiter(self.page, 'ID', 'zmf', 'zmf2_bitmap_id', data, parent)
		return len(data)

	def parse_text_styles_doc(self, data, parent):
		pass

	def parse_doc(self, data, parent):
		off = self._parse_header(data, 0, parent)
		off = self._parse_object(data, off, parent, 'Default color?')
		off = self._parse_dimensions(data, off, parent)
		off += 4 # something
		off = self._parse_data(data, off, parent)
		off += 4 # something
		off = self._parse_object(data, off, parent, 'Color palette')
		off += 0x4c # something
		off = self._parse_object(data, off, parent, 'Page')

	def parse_pages_doc(self, data, parent):
		pass

	def parse_color_palette(self, data, parent):
		off = self._parse_object(data, 0, parent, 'Color')
		if off < len(data):
			(length, off) = rdata(data, off, '<I')
			add_pgiter(self.page, 'Palette name?', 'zmf', 'zmf2_name', data[off - 4:off + int(length)], parent)
		return off + int(length)

	def parse_color(self, data, parent):
		(length, off) = rdata(data, 0xd, '<I')
		name_str = 'Color'
		if length > 1:
			(name, off) = rdata(data, off, '%ds' % (int(length) - 1))
			name_str += ' (%s)' % unicode(name, 'cp1250')
		add_pgiter(self.page, name_str, 'zmf', 'zmf2_color', data, parent)
		return len(data)

	def parse_ellipse(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Bounding box', 'zmf', 'zmf2_bbox', data[off:off + 0x20], parent)
		return off + 0x20

	def parse_image(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Bounding box', 'zmf', 'zmf2_bbox', data[off:off + 0x20], parent)
		return off + 0x20

	def parse_layer(self, data, parent):
		off = self._parse_object(data, 0, parent, 'Shape')
		(length, off) = rdata(data, off, '<I')
		add_pgiter(self.page, 'Layer name', 'zmf', 'zmf2_name', data[off - 4:off + int(length)], parent)
		return off + int(length)

	def parse_page(self, data, parent):
		off = self._parse_object(data, 0, parent, 'Layer')
		off = self._parse_object(data, off, parent, 'Something')
		off += 8
		(length, off) = rdata(data, off, '<I')
		add_pgiter(self.page, 'Trailer', 'zmf', 0, data[off - 12:off + length], parent)
		return off + length

	def parse_polygon(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Dimensions', 'zmf', 'zmf2_polygon', data[off:], parent)
		return len(data)

	def parse_polyline(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Points', 'zmf', 'zmf2_points', data[off:], parent)
		return len(data)

	def parse_rectangle(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Bounding box', 'zmf', 'zmf2_bbox', data[off:off + 0x20], parent)
		return off + 0x20

	def parse_star(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Dimensions', 'zmf', 'zmf2_star', data[off:], parent)
		return len(data)

	def parse_group(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Shapes', 'zmf', 'zmf2_group', data[off:], parent)
		return len(data)

	def parse_pen(self, data, parent):
		add_pgiter(self.page, 'Pen', 'zmf', 'zmf2_pen', data[0:0x10], parent)
		off = self._parse_object(data, 0x10, parent)
		return off

	def parse_fill(self, data, parent):
		add_pgiter(self.page, 'Fill', 'zmf', 'zmf2_fill', data[0:0x14], parent)
		off = self._parse_object(data, 0x14, parent)
		while off + 0x2c < len(data):
			off += 4
			off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Fill trailer', 'zmf', 'zmf2_fill_trailer', data[len(data) - 0x28:len(data)], parent)
		return len(data)

	def parse_shadow(self, data, parent):
		add_pgiter(self.page, 'Shadow', 'zmf', 'zmf2_shadow', data[0:0x14], parent)
		off = self._parse_object(data, 0x14, parent)
		return off

	def parse_table(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Bounding box', 'zmf', 'zmf2_bbox', data[off:off + 0x20], parent)
		off += 0x20
		add_pgiter(self.page, 'Def', 'zmf', 'zmf2_table', data[off:], parent)
		return off

	def parse_text_frame(self, data, parent):
		off = self._parse_object(data, 0, parent)
		off = self._parse_object(data, off, parent)
		off = self._parse_object(data, off, parent)
		add_pgiter(self.page, 'Bounding box', 'zmf', 'zmf2_bbox', data[off:off + 0x20], parent)
		off += 0x20
		(count, off) = rdata(data, off, '<I')

		chars = []
		chars_len = 0
		i = 0
		while i < int(count):
			(length, off) = rdata(data, off, '<I')
			i += 1
			chars.append(data[off - 4:off + int(length)])
			chars_len += 4 + int(length)
			off += int(length)

		charsiter = add_pgiter(self.page, 'Characters', 'zmf', 0, data[off:off + chars_len], parent)
		i = 0
		while i != len(chars):
			add_pgiter(self.page, 'Character %d' % (i + 1), 'zmf', 'zmf2_character', chars[i], charsiter)
			i += 1

		return off

	def _parse_file(self, data, parent):
		# TODO: this is probably set of flags
		(typ, off) = rdata(data, 4, '<H')
		if typ == 0x4:
			update_pgiter_type(self.page, 'zmf', 'zmf2_compressed_file', parent)
			off += 10
			(size, off) = rdata(data, off, '<I')
			assert off == 0x14
			assert off + int(size) <= len(data)
			end = off + int(size)
			compressed = data[off:end]
			try:
				content = zlib.decompress(compressed)
				dataiter = add_pgiter(self.page, 'Data', 'zmf', 0, content, parent)
				self.parser(self, content, dataiter)
			except zlib.error:
				print("decompression failed")
			if end < len(data):
				# TODO: is this actually a list of compressed blocks?
				add_pgiter(self.page, 'Tail', 'zmf', 0, data[end:], parent)
		else:
			update_pgiter_type(self.page, 'zmf', 'zmf2_file', parent)

	def _parse_header(self, data, offset, parent):
		(version_hint, off) = rdata(data, 4, '<I')
		# All v.2 files I've seen have 5 there, while v.3 files have 8
		if version_hint == 5:
			base_length = 0x4c
		elif version_hint == 8:
			base_length = 0x70
		(layer_name_length, off) = rdata(data, 0x38, '<I')
		length = base_length + layer_name_length
		add_pgiter(self.page, 'Header', 'zmf', 'zmf2_doc_header', data[offset:length], parent)
		return length

	def _parse_object(self, data, offset, parent, name=None, handler=None):
		off = offset
		(size, off) = rdata(data, offset, '<I')

		name_str = name

		# TODO: this is highly speculative
		(typ, off) = rdata(data, off, '<I')
		(subtyp, off) = rdata(data, off, '<I')
		count = 0
		if typ == 4 and subtyp == 3:
			header_size = 0x18
			off += 4
			(obj, off) = rdata(data, off, '<I')
			if not handler and zmf2_handlers.has_key(int(obj)):
				handler = zmf2_handlers[int(obj)]
			if zmf2_objects.has_key(int(obj)):
				name_str = '%s object' % zmf2_objects[int(obj)]
		elif typ == 4 and subtyp == 4:
			header_size = 0x14
			off += 4
			(count, off) = rdata(data, off, '<I')
			name_str = name + 's'
		elif typ == 8 and subtyp == 5:
			header_size = 0x1c
			off += 8
			(count, off) = rdata(data, off, '<I')
		else:
			print("object of unknown type (%d, %d) at %x" % (typ, subtyp, offset))
			header_size = 0

		if not name_str:
			name_str = 'Unknown object'

		showid = 0
		if header_size != 0:
			showid = 'zmf2_obj_header'
		objiter = add_pgiter(self.page, name_str, 'zmf', showid, data[offset:offset + int(size)], parent)

		content_data = data[offset + header_size:offset + int(size)]
		if handler:
			content_offset = handler(self, content_data, objiter)
		elif int(count) > 0:
			content_offset = self._parse_object_list(content_data, objiter, int(count), name)
		else:
			content_offset = 0

		if content_offset < len(content_data):
			add_pgiter(self.page, 'Unknown content', 'zmf', 0, content_data[content_offset:], objiter)

		return offset + int(size)

	def _parse_object_list(self, data, parent, n, name='Object'):
		off = 0
		i = 0
		while i < n:
			off = self._parse_object(data, off, parent, '%s %d' % (name, (i + 1)))
			i += 1
		return off

	def _parse_data(self, data, offset, parent):
		off = offset
		(size, off) = rdata(data, offset, '<I')
		add_pgiter(self.page, 'Unknown data', 'zmf', 'zmf2_data', data[offset:offset + int(size)], parent)
		return offset + int(size)

	def _parse_dimensions(self, data, offset, parent):
		off = offset
		(size, off) = rdata(data, offset, '<I')
		add_pgiter(self.page, 'Dimensions', 'zmf', 'zmf2_doc_dimensions', data[offset:offset + int(size)], parent)
		return offset + int(size)

zmf2_handlers = {
	0x3: ZMF2Parser.parse_page,
	0x4: ZMF2Parser.parse_layer,
	0x8: ZMF2Parser.parse_rectangle,
	0x9: ZMF2Parser.parse_image,
	0xa: ZMF2Parser.parse_color,
	0xc: ZMF2Parser.parse_fill,
	0xe: ZMF2Parser.parse_polyline,
	0x10: ZMF2Parser.parse_ellipse,
	0x11: ZMF2Parser.parse_star,
	0x12: ZMF2Parser.parse_polygon,
	0x13: ZMF2Parser.parse_text_frame,
	0x14: ZMF2Parser.parse_table,
	0x16: ZMF2Parser.parse_pen,
	0x18: ZMF2Parser.parse_shadow,
	0x1e: ZMF2Parser.parse_group,
	0x100: ZMF2Parser.parse_color_palette,
	0x201: ZMF2Parser.parse_bitmap_def,
}

zmf4_objects = {
	# gap
	0xa: "Fill",
	0xb: "Transparency",
	0xc: "Pen",
	0xd: "Shadow",
	0xe: "Bitmap",
	0xf: "Arrow",
	0x10: "Font",
	0x11: "Paragraph",
	0x12: "Text",
	# gap
	0x1e: "Preview bitmap?",
	# gap
	0x21: "Start of page",
	0x22: "Guidelines",
	0x23: "End of page",
	0x24: "Start of layer",
	0x25: "End of layer",
	0x26: "View",
	0x27: "Document settings",
	0x28: "Color palette",
	# gap
	0x32: "Rectangle",
	0x33: "Ellipse",
	0x34: "Polygon / Star",
	# gap
	0x36: "Curve",
	0x37: "Image",
	# gap
	0x3a: "Text frame",
	0x3b: "Table",
	# gap
	0x41: "Start of group",
	0x42: "End of group/blend",
	0x43: "Start of blend",
}

# defined later
zmf4_handlers = {}

class ZMF4Parser(object):

	def __init__(self, data, page, parent):
		self.data = data
		self.page = page
		self.parent = parent
		self.preview_offset = 0

	def parse(self):
		content = self.parse_header()
		self.parse_content(content)

	def parse_header(self):
		(offset, off) = rdata(self.data, 0x20, '<I')
		(preview, off) = rdata(self.data, off, '<I')
		if int(preview) != 0:
			self.preview_offset = int(preview) - int(offset)
			assert self.preview_offset == 0x20 # this is what I see in all files
		data = self.data[0:int(offset)]
		add_pgiter(self.page, 'Header', 'zmf', 'zmf4_header', data, self.parent)
		return offset

	def parse_content(self, begin):
		data = self.data[begin:]
		content_iter = add_pgiter(self.page, 'Content', 'zmf', 0, data, self.parent)
		off = 0
		while off + 4 <= len(data):
			off = self._parse_object(data, off, content_iter)

	def parse_object(self, data, start, length, parent, typ, callback):
		self._do_parse_object(data[start:start + length], parent, typ, callback)
		return start + length

	def parse_preview_bitmap(self, data, start, length, parent, typ, callback):
		data_start = start + length
		(bmp_type, off) = rdata(data, data_start, '2s')
		assert bmp_type == 'BM'
		(size, off) = rdata(data, off, '<I')
		assert data_start + size < len(data)
		objiter = self._do_parse_object(data[start:data_start], parent, typ, callback)
		add_pgiter(self.page, 'Bitmap data', 'zmf', 'zmf4_preview_bitmap_data', data[data_start:data_start + size], objiter)
		return data_start + size

	def parse_bitmap(self, data, start, length, parent, typ, callback):
		data_start = start + length
		(something, off) = rdata(data, start + 0x20, '<I')
		has_data = bool(something)
		objiter = self._do_parse_object(data[start:data_start], parent, typ, callback)
		if has_data:
			(bmp_type, off) = rdata(data, data_start, '9s')
			assert bmp_type == 'ZonerBMIa'
			size = bmi.get_size(data[data_start:])
			assert data_start + size < len(data)
			bmi.open(data[data_start:data_start + size], self.page, objiter)
			length += size
		return start + length

	def _parse_object(self, data, start, parent):
		(length, off) = rdata(data, start, '<I')
		(typ, off) = rdata(data, off, '<H')
		if start + length <= len(data):
			if zmf4_handlers.has_key(int(typ)):
				(handler, callback) = zmf4_handlers[int(typ)]
				return handler(self, data, start, length, parent, typ, callback)
			else:
				self._do_parse_object(data[start:start + length], parent, typ, 'zmf4_obj')
				return start + length

	def _do_parse_object(self, data, parent, typ, callback):
		if zmf4_objects.has_key(typ):
			obj = zmf4_objects[typ]
		else:
			obj = 'Unknown object 0x%x' % typ
		obj_str = obj
		if len(data) >= 0x1c:
			(oid, off) = rdata(data, 0x18, '<I')
			if int(oid) != 0xffffffff:
				obj_str = '%s (0x%x)' % (obj, oid)
		return add_pgiter(self.page, obj_str, 'zmf', callback, data, parent)

zmf4_handlers = {
	0xA: (ZMF4Parser.parse_object, 'zmf4_obj_fill'),
	0xB: (ZMF4Parser.parse_object, 'zmf4_obj_fill'),
	0xC: (ZMF4Parser.parse_object, 'zmf4_obj_pen'),
	0xD: (ZMF4Parser.parse_object, 'zmf4_obj_shadow'),
	0xe: (ZMF4Parser.parse_bitmap, 'zmf4_obj_bitmap'),
	0xf: (ZMF4Parser.parse_object, 'zmf4_obj_arrow'),
	0x10: (ZMF4Parser.parse_object, 'zmf4_obj_font'),
	0x11: (ZMF4Parser.parse_object, 'zmf4_obj_paragraph'),
	0x12: (ZMF4Parser.parse_object, 'zmf4_obj_text'),
	0x1e: (ZMF4Parser.parse_preview_bitmap, 'zmf4_obj'),
	0x22: (ZMF4Parser.parse_object, 'zmf4_obj_guidelines'),
	0x24: (ZMF4Parser.parse_object, 'zmf4_obj_start_layer'),
	0x26: (ZMF4Parser.parse_object, 'zmf4_view'),
	0x27: (ZMF4Parser.parse_object, 'zmf4_obj_doc_settings'),
	0x28: (ZMF4Parser.parse_object, 'zmf4_obj_color_palette'),
	0x32: (ZMF4Parser.parse_object, 'zmf4_obj_rectangle'),
	0x33: (ZMF4Parser.parse_object, 'zmf4_obj_ellipse'),
	0x34: (ZMF4Parser.parse_object, 'zmf4_obj_polygon'),
	0x36: (ZMF4Parser.parse_object, 'zmf4_obj_curve'),
	0x37: (ZMF4Parser.parse_object, 'zmf4_obj_image'),
	0x3a: (ZMF4Parser.parse_object, 'zmf4_obj_text_frame'),
	0x3b: (ZMF4Parser.parse_object, 'zmf4_obj_table'),
	0x41: (ZMF4Parser.parse_object, 'zmf4_obj_start_group'),
	0x43: (ZMF4Parser.parse_object, 'zmf4_obj_blend'),
}

def _add_zmf2_string(hd, size, data, offset, name):
	(length, off) = rdata(data, offset, '<I')
	add_iter(hd, '%s length' % name, length, off - 4, 4, '<I')
	text_len = int(length) - 1
	if text_len > 1:
		(text, off) = rdata(data, off, '%ds' % text_len)
		add_iter(hd, name, unicode(text, 'cp1250'), off - text_len, text_len + 1, '%ds' % text_len)
	else:
		add_iter(hd, name, '', off, 1, '%ds' % text_len)
	return off + 1

def add_zmf2_data(hd, size, data):
	(length, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Length', length, off - 4, 4, '<I')

def add_zmf2_bbox(hd, size, data):
	(tl_x, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Top left X', tl_x, off - 4, 4, '<I')
	(tl_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Top left Y', tl_y, off - 4, 4, '<I')
	(tr_x, off) = rdata(data, off, '<I')
	add_iter(hd, 'Top right X', tr_x, off - 4, 4, '<I')
	(tr_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Top right Y', tr_y, off - 4, 4, '<I')
	(br_x, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom right X', br_x, off - 4, 4, '<I')
	(br_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom right Y', br_y, off - 4, 4, '<I')
	(bl_x, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom left X', bl_x, off - 4, 4, '<I')
	(bl_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom left Y', bl_y, off - 4, 4, '<I')

def add_zmf2_bitmap_db(hd, size, data):
	(count, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Number of bitmaps?', count, off - 4, 4, '<I')

def add_zmf2_bitmap_id(hd, size, data):
	(bid, off) = rdata(data, 0, '<I')
	add_iter(hd, 'ID', bid, off - 4, 4, '<I')

def add_zmf2_character(hd, size, data):
	(length, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Length', length, off - 4, 4, '<I')
	(c, off) = rdata(data, off, '1s')
	add_iter(hd, 'Character', unicode(c, 'cp1250'), off - 1, 1, '1s')

def add_zmf2_header(hd, size, data):
	(length, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Length?', length, off - 4, 4, '<I')
	off += 6
	(version, off) = rdata(data, off, '<H')
	add_iter(hd, 'Version', version, off - 2, 2, '<H')
	(sig, off) = rdata(data, off, '<I')
	add_iter(hd, 'Signature', '0x%x' % sig, off - 4, 4, '<I')

def add_zmf2_file(hd, size, data):
	(size, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Size', size, off - 4, 4, '<I')
	(typ, off) = rdata(data, off, '<H')
	add_iter(hd, 'Type', typ, off - 2, 2, '<H')

def add_zmf2_compressed_file(hd, size, data):
	add_zmf2_file(hd, size, data)
	off = 0x10
	(data_size, off) = rdata(data, off, '<I')
	add_iter(hd, 'Size of data', data_size, off - 4, 4, '<I')

def add_zmf2_doc_header(hd, size, data):
	off = 8
	(count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Total number of objects', count, off - 4, 4, '<I')
	off = 0x28
	(lr_margin, off) = rdata(data, off, '<I')
	add_iter(hd, 'Left & right page margin?', lr_margin, off - 4, 4, '<I')
	(tb_margin, off) = rdata(data, off, '<I')
	add_iter(hd, 'Top & bottom page margin?', tb_margin, off - 4, 4, '<I')
	off += 8
	off = _add_zmf2_string(hd, size, data, off, 'Default layer name?')
	(tl_x, off) = rdata(data, off, '<I')
	add_iter(hd, 'Page top left X?', tl_x, off - 4, 4, '<I')
	(tl_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Page top left Y?', tl_y, off - 4, 4, '<I')
	(br_x, off) = rdata(data, off, '<I')

def add_zmf2_doc_dimensions(hd, size, data):
	(size, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Size', size, off - 4, 4, '<I')
	off += 8
	(cwidth, off) = rdata(data, off, '<I')
	add_iter(hd, 'Canvas width', cwidth, off - 4, 4, '<I')
	(cheight, off) = rdata(data, off, '<I')
	add_iter(hd, 'Canvas height', cheight, off - 4, 4, '<I')
	off += 4
	(tl_x, off) = rdata(data, off, '<I')
	add_iter(hd, 'Page top left X', tl_x, off - 4, 4, '<I')
	(tl_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Page top left Y', tl_y, off - 4, 4, '<I')
	if off < size:
		(br_x, off) = rdata(data, off, '<I')
		add_iter(hd, 'Page bottom right X', br_x, off - 4, 4, '<I')
		(br_y, off) = rdata(data, off, '<I')
		add_iter(hd, 'Page bottom right Y', br_y, off - 4, 4, '<I')

def add_zmf2_obj_header(hd, size, data):
	(size, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Size', size, off - 4, 4, '<I')
	(typ, off) = rdata(data, off, '<I')
	add_iter(hd, 'Type', typ, off - 4, 4, '<I')
	(subtyp, off) = rdata(data, off, '<I')
	add_iter(hd, 'Subtype', subtyp, off - 4, 4, '<I')
	if typ == 4 and subtyp == 3:
		off += 4
		(obj_type, off) = rdata(data, off, '<I')
		add_iter(hd, 'Object type', obj_type, off - 4, 4, '<I')
	elif typ == 4 and subtyp == 4:
		off += 4
		(count, off) = rdata(data, off, '<I')
		add_iter(hd, 'Number of subobjects', count, off - 4, 4, '<I')
	elif typ == 8 and subtyp == 5:
		off += 8
		(count, off) = rdata(data, off, '<I')
		add_iter(hd, 'Number of subobjects', count, off - 4, 4, '<I')

def add_zmf2_color(hd, size, data):
	off = 0xd
	_add_zmf2_string(hd, size, data, off, 'Name')

def add_zmf2_name(hd, size, data):
	_add_zmf2_string(hd, size, data, 0, 'Name')

def add_zmf2_points(hd, size, data):
	(count, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Number of points', count, off - 4, 4, '<I')
	i = 0
	while i < int(count):
		(x, off) = rdata(data, off, '<I')
		add_iter(hd, 'Point %d X' % (i + 1), x, off - 4, 4, '<I')
		(y, off) = rdata(data, off, '<I')
		add_iter(hd, 'Point %d Y' % (i + 1), y, off - 4, 4, '<I')
		off += 8
		i += 1

def add_zmf2_polygon(hd, size, data):
	(tl_x, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Top left X?', tl_x, off - 4, 4, '<I')
	(tl_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Top left Y?', tl_y, off - 4, 4, '<I')
	(br_x, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom right X?', br_x, off - 4, 4, '<I')
	(br_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom right Y?', br_y, off - 4, 4, '<I')
	(points, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of edges', points, off - 4, 4, '<I')

def add_zmf2_star(hd, size, data):
	(tl_x, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Top left X?', tl_x, off - 4, 4, '<I')
	(tl_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Top left Y?', tl_y, off - 4, 4, '<I')
	(br_x, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom right X?', br_x, off - 4, 4, '<I')
	(br_y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom right Y?', br_y, off - 4, 4, '<I')
	(points, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of points', points, off - 4, 4, '<I')
	(angle, off) = rdata(data, off, '<I')
	add_iter(hd, 'Point angle?', angle, off - 4, 4, '<I')

def add_zmf2_group(hd, size, data):
	off = 12
	(count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of shapes?', count, off - 4, 4, '<I')
	off += 8
	(gidx, off) = rdata(data, off, '<I')
	add_iter(hd, 'Group shape index?', (gidx + 1), off - 4, 4, '<I')
	(count2, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of shapes (again)?', count2, off - 4, 4, '<I')
	for i in range(1, count + 1):
		off += 4
		(sidx, off) = rdata(data, off, '<I')
		add_iter(hd, 'Shape %d index' % i, (sidx + 1), off - 4, 4, '<I')

def add_zmf2_pen(hd, size, data):
	off = 0
	type_map = {0: 'solid', 1: 'dash', 2: 'long dash', 3: 'dash dot', 4: 'dash dot dot'}
	(typ, off) = rdata(data, off, '<I')
	add_iter(hd, 'Type', key2txt(typ, type_map), off - 4, 4, '<I')
	(width, off) = rdata(data, off, '<I')
	add_iter(hd, 'Width', width, off - 4, 4, '<I')
	arrow_map = {0: 'none'}
	(start, off) = rdata(data, off, '<I')
	add_iter(hd, 'Start arrow', key2txt(start, arrow_map), off - 4, 4, '<I')
	(end, off) = rdata(data, off, '<I')
	add_iter(hd, 'End arrow', key2txt(end, arrow_map), off - 4, 4, '<I')

def add_zmf2_fill(hd, size, data):
	off = 0
	type_map = {1: 'solid', 2: 'linear gradient'}
	(typ, off) = rdata(data, off, '<I')
	add_iter(hd, 'Type?', key2txt(typ, type_map), off - 4, 4, '<I')

def add_zmf2_fill_trailer(hd, size, data):
	pass

def add_zmf2_shadow(hd, size, data):
	off = 0
	unit_map = {0: 'mm', 1: '%'}
	(unit, off) = rdata(data, off, '<I')
	add_iter(hd, 'Offset unit', key2txt(unit, unit_map), off - 4, 4, '<I')
	type_map = {0: 'none', 1: 'color', 2: 'brightness'}
	(typ, off) = rdata(data, off, '<I')
	add_iter(hd, 'Type', key2txt(typ, type_map), off - 4, 4, '<I')
	(horiz, off) = rdata(data, off, '<I')
	add_iter(hd, 'Horizontal offset', horiz, off - 4, 4, '<I')
	(vert, off) = rdata(data, off, '<I')
	add_iter(hd, 'Vertical offset', vert, off - 4, 4, '<I')
	(brightness, off) = rdata(data, off, '<I')
	add_iter(hd, 'Brightness', '%d%%' % brightness, off - 4, 4, '<I')

def add_zmf2_table(hd, size, data):
	off = 4
	(rows, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of rows', rows, off - 4, 4, '<I')
	(cols, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of columns', cols, off - 4, 4, '<I')

	off += 8

	for i in range(int(cols)):
		(width, off) = rdata(data, off, '<I')
		add_iter(hd, 'Width of column %d' % (i + 1), width, off - 4, 4, '<I')
		off += 4

	for i in range(int(rows)):
		(height, off) = rdata(data, off, '<I')
		add_iter(hd, 'Height of row %d' % (i + 1), height, off - 4, 4, '<I')
		off += 0x2c
		for j in range(int(cols)):
			(length, off) = rdata(data, off, '<I')
			add_iter(hd, 'String length', length, off - 4, 4, '<I')
			fix = 0
			if int(length) > 0:
				(text, off) = rdata(data, off, '%ds' % int(length))
				add_iter(hd, 'Content', text, off - int(length), int(length), '%ds' % int(length))
				off += 0x29
				fix = 0x29
		off -= fix
		off += 5

def add_zmf4_preview_bitmap_data(hd, size, data):
	(typ, off) = rdata(data, 0, '2s')
	add_iter(hd, 'Type', typ, off - 2, 2, '2s')
	(size, off) = rdata(data, off, '<I')
	add_iter(hd, 'Size', size, off - 4, 4, '<I')

def add_zmf4_header(hd, size, data):
	off = 8
	(sig, off) = rdata(data, off, '<I')
	add_iter(hd, 'Signature', '0x%x' % sig, off - 4, 4, '<I')
	(version, off) = rdata(data, off, '<I')
	add_iter(hd, 'Version', version, off - 4, 4, '<I')
	off += 12
	(count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Count of objects', count, off - 4, 4, '<I')
	(content, off) = rdata(data, off, '<I')
	add_iter(hd, 'Start of content', content, off - 4, 4, '<I')
	(preview, off) = rdata(data, off, '<I')
	add_iter(hd, 'Start of preview bitmap', preview, off - 4, 4, '<I')
	off += 16
	(size, off) = rdata(data, off, '<I')
	add_iter(hd, 'File size', size, off - 4, 4, '<I')

def _zmf4_obj_header(hd, size, data):
	(size, off) = rdata(data, 0, '<I')
	add_iter(hd, 'Size', size, off - 4, 4, '<I')
	(typ, off) = rdata(data, off, '<H')
	if zmf4_objects.has_key(typ):
		obj = zmf4_objects[typ]
	else:
		obj = 'Unknown object 0x%x' % typ
	add_iter(hd, 'Type', obj, off - 2, 2, '<I')
	off = 0xc
	(ref_obj_count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Count of referenced objects', ref_obj_count, off - 4, 4, '<I')
	(refs_start, off) = rdata(data, off, '<I')
	add_iter(hd, 'Start of refs list', refs_start, off - 4, 4, '<I')
	(ref_types_start, off) = rdata(data, off, '<I')
	add_iter(hd, 'Start of ref types list', ref_types_start, off - 4, 4, '<I')
	(oid, off) = rdata(data, off, '<I')
	add_iter(hd, 'ID', ref2txt(oid), off - 4, 4, '<I')
	return off

def _zmf4_obj_refs(hd, size, data, type_map):
	off = 0xc
	(ref_obj_count, off) = rdata(data, off, '<I')
	off_start = size - 8 * ref_obj_count
	off_tag = off_start + 4 * ref_obj_count
	types = []
	# Determine names
	off = off_tag
	i = 1
	while i <= ref_obj_count:
		(id, off) = rdata(data, off, '<I')
		if id == 0xffffffff:
			typ = 'Unused'
		else:
			typ = key2txt(id, type_map)
		types.append(typ)
		i += 1
	# Show refs and names
	i = 1
	off = off_start
	while i <= ref_obj_count:
		(ref, off) = rdata(data, off, '<I')
		add_iter(hd, '%s ref' % types[i - 1], ref2txt(ref), off - 4, 4, '<I')
		i += 1
	i = 1
	assert off == off_tag
	while i <= ref_obj_count:
		(id, off) = rdata(data, off, '<I')
		add_iter(hd, 'Ref %d type' % i, types[i - 1], off - 4, 4, '<I')
		i += 1

shape_ref_types = {
	1: 'Fill',
	2: 'Pen',
	3: 'Shadow',
	4: 'Transparency',
}

def _zmf4_obj_bbox(hd, size, data, off):
	(width, off) = rdata(data, off, '<I')
	add_iter(hd, 'Width', width, off - 4, 4, '<I')
	(height, off) = rdata(data, off, '<I')
	add_iter(hd, 'Height', height, off - 4, 4, '<I')
	i = 1
	while i <= 4:
		# points can be in different order depending on how the object was created (mouse cursor movement direction)
		(x, off) = rdata(data, off, '<I')
		add_iter(hd, 'Bounding box corner %d X' % i, x, off - 4, 4, '<I')
		(y, off) = rdata(data, off, '<I')
		add_iter(hd, 'Bounding box corner %d Y' % i, y, off - 4, 4, '<I')
		i += 1
	return off

def _zmf4_curve_type_list(hd, size, data, off, points, name='Point'):
	types = {
		1: 'Line to',
		2: 'Bezier curve point 1',
		3: 'Bezier curve point 2',
		4: 'Bezier curve point 3'
	}
	i = 1
	while i <= points:
		(type, off) = rdata(data, off, '<I')
		if type != 0x64:
			add_iter(hd, '%s %d type' % (name, i + 1), key2txt(type, types), off - 4, 4, '<I')
		i += 1
	return off

def _zmf4_curve_data(hd, size, data, off):
	(path_len, off) = rdata(data, off, '<I')
	add_iter(hd, 'Length of path data?', path_len, off - 4, 4, '<I')
	off += 8
	(components, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of components', components, off - 4, 4, '<I')
	points = 0
	i = 1
	while i <= components:
		off += 8
		(count, off) = rdata(data, off, '<I')
		points += count
		add_iter(hd, 'Number of points of comp. %d' % i, count, off - 4, 4, '<I')
		(closed, off) = rdata(data, off, '<I')
		add_iter(hd, 'Comp. %d closed?' % i, bool(closed), off - 4, 4, '<I')
		i += 1
	i = 1
	while i <= points:
		(x, off) = rdata(data, off, '<I')
		add_iter(hd, 'Point %d X' % i, x, off - 4, 4, '<I')
		(y, off) = rdata(data, off, '<I')
		add_iter(hd, 'Point %d Y' % i, y, off - 4, 4, '<I')
		i += 1
	off = _zmf4_curve_type_list(hd, size, data, off, points)
	return off

def add_zmf4_obj(hd, size, data):
	_zmf4_obj_header(hd, size, data)

def add_zmf4_obj_start_layer(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	flags_map = {0x1: 'visible', 0x2: 'lock', 0x4: 'print'}
	(flags, off) = rdata(data, off, '<B')
	add_iter(hd, 'Flags', bflag2txt(flags, flags_map), off - 1, 1, '<B')
	off += 3
	(name_offset, off) = rdata(data, off, '<I')
	add_iter(hd, 'Name offset', name_offset, off - 4, 4, '<I')
	(order, off) = rdata(data, off, '<I')
	add_iter(hd, 'Layer order', order, off - 4, 4, '<I')
	name_length = size - off
	(name, off) = rdata(data, off, '%ds' % name_length)
	add_iter(hd, 'Name', name, off - name_length, name_length, '%ds' % name_length)

def add_zmf4_obj_doc_settings(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	(length, off) = rdata(data, off, '<I')
	add_iter(hd, 'Data length?', length, off - 4, 4, '<I')
	flags_map = {
		0x1: 'show margins',
		0x2: 'print margins',
		0x4: 'show prepress marks',
		0x8: 'print prepress marks',
		0x10: 'show guidelines',
		0x20: 'lock guidelines',
		0x40: 'snap to guidelines',
		0x80: 'show master guidelines',
		0x100: 'lock master guidelines',
		0x200: 'snap to master guidelines',
		0x400: 'show master page',
		0x800: 'print master page',
	}
	(flags, off) = rdata(data, off, '<I')
	add_iter(hd, 'Flags', bflag2txt(flags, flags_map), off - 4, 4, '<I')
	marks_flags_map = {
		0x1: 'show fit marks',
		0x2: 'show cut marks',
		0x4: 'show doc info',
		0x8: 'show date&time',
		0x10: 'show ref colors',
		0x20: 'print fit marks',
		0x40: 'print cut marks',
		0x80: 'print doc info',
		0x100: 'print date&time',
		0x200: 'print ref colors',
	}
	(marks_flags, off) = rdata(data, off, '<I')
	add_iter(hd, 'Prepress marks flags', bflag2txt(marks_flags, marks_flags_map), off - 4, 4, '<I')
	off += 0x14
	(color, off) = rdata(data, off, '3s')
	add_iter(hd, 'Page color (RGB)', d2hex(color), off - 3, 3, '3s')
	off += 5
	(width, off) = rdata(data, off, '<I')
	# Note: maximum possible page size is 40305.08 x 28500 mm. Do not ask me why...
	add_iter(hd, 'Page width', width, off - 4, 4, '<I')
	(height, off) = rdata(data, off, '<I')
	add_iter(hd, 'Page height', height, off - 4, 4, '<I')
	# Note: the margins are relative to respective border. That means
	# that right/bottom margins are typically (always?) negative.
	(left_margin, off) = rdata(data, off, '<i')
	add_iter(hd, 'Left page margin', left_margin, off - 4, 4, '<i')
	(top_margin, off) = rdata(data, off, '<i')
	add_iter(hd, 'Top page margin', top_margin, off - 4, 4, '<i')
	(right_margin, off) = rdata(data, off, '<i')
	add_iter(hd, 'Right page margin', right_margin, off - 4, 4, '<i')
	(bottom_margin, off) = rdata(data, off, '<i')
	add_iter(hd, 'Bottom page margin', bottom_margin, off - 4, 4, '<i')
	(origin_x, off) = rdata(data, off, '<i')
	add_iter(hd, 'Origin X', origin_x, off - 4, 4, '<i')
	(origin_y, off) = rdata(data, off, '<i')
	add_iter(hd, 'Origin Y', origin_y, off - 4, 4, '<i')
	off += 0x4
	grid_flags_map = {0x1: 'dots', 0x2: 'lines', 0x4: 'snap', 0x8: 'show',}
	(grid_flags, off) = rdata(data, off, '<B')
	add_iter(hd, 'Grid flags', bflag2txt(grid_flags, grid_flags_map), off - 1, 1, '<B')
	off += 3
	(h_density, off) = rdata(data, off, '<I')
	add_iter(hd, 'Grid h. density', h_density, off - 4, 4, '<I')
	(v_density, off) = rdata(data, off, '<I')
	add_iter(hd, 'Grid v. density', v_density, off - 4, 4, '<I')
	(dot_step, off) = rdata(data, off, '<I')
	add_iter(hd, 'Grid dot step', dot_step, off - 4, 4, '<I')
	(line_step, off) = rdata(data, off, '<I')
	add_iter(hd, 'Grid line step', line_step, off - 4, 4, '<I')
	off += 0xc
	# The page is placed on a much bigger canvas
	# NOTE: it seems that positions are in respect to canvas, not to page.
	(cwidth, off) = rdata(data, off, '<I')
	add_iter(hd, 'Canvas width', cwidth, off - 4, 4, '<I')
	(cheight, off) = rdata(data, off, '<I')
	add_iter(hd, 'Canvas height', cheight, off - 4, 4, '<I')
	(left, off) = rdata(data, off, '<I')
	add_iter(hd, 'Offset of left side of page', left, off - 4, 4, '<I')
	(top, off) = rdata(data, off, '<I')
	add_iter(hd, 'Offset of top side of page', top, off - 4, 4, '<I')
	(right, off) = rdata(data, off, '<I')
	add_iter(hd, 'Offset of right side of page', right, off - 4, 4, '<I')
	(bottom, off) = rdata(data, off, '<I')
	add_iter(hd, 'Offset of bottom side of page', bottom, off - 4, 4, '<I')
	(left_offset, off) = rdata(data, off, '<I')
	add_iter(hd, 'Real offset of left side of page?', left_offset, off - 4, 4, '<I')
	(top_offset, off) = rdata(data, off, '<I')
	add_iter(hd, 'Real offset of top side of page?', top_offset, off - 4, 4, '<I')

def add_zmf4_obj_color_palette(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	(data_size, off) = rdata(data, off, '<I')
	add_iter(hd, 'Data size?', data_size, off - 4, 4, '<I')
	(name_offset, off) = rdata(data, off, '<I')
	add_iter(hd, 'Name offset?', name_offset, off - 4, 4, '<I')
	name_length = data_size - name_offset
	(count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Color count', count, off - 4, 4, '<I')
	i = 1
	while i <= count:
		off += 4
		add_iter(hd, 'Color %d' % i, d2hex(data[off:off+4]), off, 4, '4s')
		off += 8
		i += 1
	(name, off) = rdata(data, off, '%ds' % name_length)
	add_iter(hd, 'Name', name, off - name_length, name_length, '%ds' % name_length)

def add_zmf4_obj_fill(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 4
	(data_size, off) = rdata(data, off, '<I')
	add_iter(hd, 'Data size?', data_size, off - 4, 4, '<I')
	fill_types = {
		1: 'Solid',
		2: 'Linear',
		3: 'Radial',
		4: 'Conical',
		5: 'Cross-shaped',
		6: 'Rectangular',
		7: 'Flexible',
		8: 'Bitmap',
	}
	(type, off) = rdata(data, off, '<I')
	add_iter(hd, 'Fill type', key2txt(type, fill_types), off - 4, 4, '<I')
	if type == 1:
		off = 0x30
		add_iter(hd, 'Color (RGB)', d2hex(data[off:off+3]), off, 3, '3s')
	else:
		(transform, off) = rdata(data, off, '<I')
		add_iter(hd, 'Transform with object', bool(transform), off - 4, 4, '<I')
		(stop_count, off) = rdata(data, off, '<I')
		add_iter(hd, 'Stop count', stop_count, off - 4, 4, '<I')
		if type == 8:
			(width, off) = rdata(data, off, '<I')
			add_iter(hd, 'Width?', width, off - 4, 4, '<I')
			(height, off) = rdata(data, off, '<I')
			add_iter(hd, 'Height?', height, off - 4, 4, '<I')
		elif type != 2:
			off += 4
			(cx, off) = rdata(data, off, '<f')
			add_iter(hd, 'Center x (%)', cx, off - 4, 4, '<f')
			(cy, off) = rdata(data, off, '<f')
			add_iter(hd, 'Center y (%)', cy, off - 4, 4, '<f')
		if type not in {3, 7}:
			off = 0x3c
			(angle, off) = rdata(data, off, '<f')
			add_iter(hd, 'Angle (rad)', angle, off - 4, 4, '<f')
		off = 0x40
		(steps, off) = rdata(data, off, '<I')
		add_iter(hd, 'Steps', steps, off - 4, 4, '<I')
		off = 0x48
		i = 1
		while i <= stop_count:
			add_iter(hd, 'Stop %d color (RGB)' % i, d2hex(data[off:off+3]), off, 3, '3s')
			off += 8
			(pos, off) = rdata(data, off, '<f')
			add_iter(hd, 'Stop %d position' % i, pos, off - 4, 4, '<f')
			off += 4
			i += 1
	ref_types = {0: 'Fill bitmap'}
	_zmf4_obj_refs(hd, size, data, ref_types)


def add_zmf4_obj_pen(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 4
	(data_size, off) = rdata(data, off, '<I')
	add_iter(hd, 'Data size?', data_size, off - 4, 4, '<I')
	(transform, off) = rdata(data, off, '<I')
	add_iter(hd, 'Transform with object', bool(transform), off - 4, 4, '<I')
	corner_types = {0: 'Miter', 1: 'Round', 2: 'Bevel'}
	(corner_type, off) = rdata(data, off, '<I')
	add_iter(hd, 'Line corner type', key2txt(corner_type, corner_types), off - 4, 4, '<I')
	caps_types = {0: 'Butt', 1: 'Flat', 2: 'Round', 3: 'Pointed'}
	(caps_type, off) = rdata(data, off, '<I')
	add_iter(hd, 'Line caps type', key2txt(caps_type, caps_types), off - 4, 4, '<I')
	(miter, off) = rdata(data, off, '<I')
	add_iter(hd, 'Miter limit', miter, off - 4, 4, '<I')
	(width, off) = rdata(data, off, '<I')
	add_iter(hd, 'Pen width', width, off - 4, 4, '<I')
	off = 0x3c
	add_iter(hd, 'Pen color (RGB)', d2hex(data[off:off+3]), off, 3, '3s')
	off = 0x48
	(angle, off) = rdata(data, off, '<f')
	add_iter(hd, 'Caligraphy angle (rad)', angle, off - 4, 4, '<f')
	(stretch, off) = rdata(data, off, '<f')
	add_iter(hd, 'Caligraphy stretch', '%2d%%' % (stretch * 100), off - 4, 4, '<f')
	off = 0x50
	(dashes, off) = rdata(data, off, '6s')
	add_iter(hd, 'Dash pattern (bits)', d2bin(dashes), off - 6, 6, '6s')
	(dist, off) = rdata(data, off, '<H')
	add_iter(hd, 'Distance between dash patterns?', dist, off - 2, 2, '<H')
	arrow_types = {
		0: 'Arrow start',
		1: 'Arrow end'
	}
	_zmf4_obj_refs(hd, size, data, arrow_types)

def add_zmf4_obj_arrow(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 8
	_zmf4_curve_data(hd, size, data, off)

def add_zmf4_obj_shadow(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 8
	shadow_types = {
		1: 'Color',
		2: 'Brightness',
		3: 'Soft',
		4: 'Transparent'
	}
	(type, off) = rdata(data, off, '<I')
	add_iter(hd, 'Shadow type', key2txt(type, shadow_types), off - 4, 4, '<I')
	(x, off) = rdata(data, off, '<I')
	add_iter(hd, 'X offset', x, off - 4, 4, '<I')
	(y, off) = rdata(data, off, '<I')
	add_iter(hd, 'Y offset', y, off - 4, 4, '<I')
	(skew, off) = rdata(data, off, '<f')
	add_iter(hd, 'Skew angle (rad)', skew, off - 4, 4, '<f')
	(transp, off) = rdata(data, off, '<f')
	add_iter(hd, 'Transparency/Brightness', transp, off - 4, 4, '<f')
	add_iter(hd, 'Color (RGB)', d2hex(data[off:off+3]), off, 3, '3s')
	off = 0x40
	(transp2, off) = rdata(data, off, '<f')
	add_iter(hd, 'Transparency (for Soft)', transp2, off - 4, 4, '<f')
	(blur, off) = rdata(data, off, '<I')
	add_iter(hd, 'Blur', blur, off - 4, 4, '<I')

def add_zmf4_obj_ellipse(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off = _zmf4_obj_bbox(hd, size, data, off)
	(begin, off) = rdata(data, off, '<f')
	add_iter(hd, 'Beginning (rad)', begin, off - 4, 4, '<f')
	(end, off) = rdata(data, off, '<f')
	add_iter(hd, 'Ending (rad)', end, off - 4, 4, '<f')
	(arc, off) = rdata(data, off, '<I')
	add_iter(hd, 'Arc (== not closed)', bool(arc), off - 4, 4, '<I')
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_obj_polygon(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off = _zmf4_obj_bbox(hd, size, data, off)
	(peaks, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of peaks', peaks, off - 4, 4, '<I')
	(count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of ?points describing one peak', count, off - 4, 4, '<I')
	off += 8
	i = 1
	while i <= count:
		(x, off) = rdata(data, off, '<f')
		add_iter(hd, 'Point/sharpness? %d X' % i, x, off - 4, 4, '<f')
		(y, off) = rdata(data, off, '<f')
		add_iter(hd, 'Point/sharpness? %d Y' % i, y, off - 4, 4, '<f')
		i += 1
	_zmf4_curve_type_list(hd, size, data, off, count, 'Point/sharpness?')
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_obj_curve(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	(garbage, off) = rdata(data, off, '40s')
	add_iter(hd, 'Unused/garbage?', '', off - 40, 40, '40s')
	_zmf4_curve_data(hd, size, data, off)
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_obj_rectangle(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off = _zmf4_obj_bbox(hd, size, data, off)
	rectangle_corner_types = {
		1: 'Normal',
		2: 'Round',
		3: 'Round In',
		4: 'Cut'
	}
	(corner_type, off) = rdata(data, off, '<I')
	add_iter(hd, 'Corner type', key2txt(corner_type, rectangle_corner_types), off - 4, 4, '<I')
	(rounding_value, off) = rdata(data, off, '<f')
	add_iter(hd, 'Rounding', '%.0f%% of shorter side\'s length' % (rounding_value * 50), off - 4, 4, '<f')
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_obj_image(hd, size, data):
	_zmf4_obj_header(hd, size, data)
	ref_types = {5: 'Bitmap'}
	ref_types.update(shape_ref_types)
	_zmf4_obj_refs(hd, size, data, ref_types)

def add_zmf4_obj_table(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off = _zmf4_obj_bbox(hd, size, data, off)
	(length, off) = rdata(data, off, '<I')
	add_iter(hd, 'Length of table data?', length, off - 4, 4, '<I')
	off += 4
	(rows, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of rows', rows, off - 4, 4, '<I')
	(cols, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of columns', cols, off - 4, 4, '<I')
	off += 8
	i = 1
	while i <= rows * cols:
		row = (i - 1) / cols + 1
		column = i - (row - 1) * cols
		cell_iter = add_iter(hd, 'Cell %d (row %d, column %d)' % (i, row, column), '', off, 20, '20s')
		off += 4 # related to vertical pos
		(fill, off) = rdata(data, off, '<I')
		add_iter(hd, 'Fill ref', ref2txt(fill), off - 4, 4, '<I', parent=cell_iter)
		(text, off) = rdata(data, off, '<I')
		add_iter(hd, 'Text ref', ref2txt(text), off - 4, 4, '<I', parent=cell_iter)
		(right_pen, off) = rdata(data, off, '<I')
		# pen with ID 0x1 is used in cells, rows and columns when they have no border
		# (0xffffffff aka None probably not used because it would not override column/row pen)
		add_iter(hd, 'Right border pen ref', ref2txt(right_pen), off - 4, 4, '<I', parent=cell_iter)
		(bottom_pen, off) = rdata(data, off, '<I')
		add_iter(hd, 'Bottom border pen ref', ref2txt(bottom_pen), off - 4, 4, '<I', parent=cell_iter)
		i += 1
	i = 1
	while i <= rows:
		row_iter = add_iter(hd, 'Row %d' % i, '', off, 12, '12s')
		off += 4
		(bottom_pen, off) = rdata(data, off, '<I')
		add_iter(hd, 'Left border pen ref', ref2txt(bottom_pen), off - 4, 4, '<I', parent=row_iter)
		(rel_height, off) = rdata(data, off, '<f')
		add_iter(hd, 'Relative height', '%.0f%%' % (100 * rel_height / rows), off - 4, 4, '<f', parent=row_iter)
		i += 1
	i = 1
	while i <= cols:
		col_iter = add_iter(hd, 'Column %d' % i, '', off, 12, '12s')
		off += 4
		(right_pen, off) = rdata(data, off, '<I')
		add_iter(hd, 'Top border pen ref', ref2txt(right_pen), off - 4, 4, '<I', parent=col_iter)
		(rel_width, off) = rdata(data, off, '<f')
		add_iter(hd, 'Relative width', '%.0f%%' % (100 * rel_width / cols), off - 4, 4, '<f', parent=col_iter)
		i += 1
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_obj_font(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 4
	fmt_map = {0x1: 'bold', 0x2: 'italic'}
	(fmt, off) = rdata(data, off, '<B')
	add_iter(hd, 'Format', bflag2txt(fmt, fmt_map), off - 1, 1, '<B')
	off += 3
	(font_size, off) = rdata(data, off, '<f')
	add_iter(hd, 'Font size', '%dpt' % font_size, off - 4, 4, '<f')
	(codepage, off) = rdata(data, off, '<I')
	add_iter(hd, 'Code page', key2txt(codepage, ms_charsets), off - 4, 4, '<I')
	font = ''
	font_pos = off
	# Note: it looks like the font name entry might be fixed size: 32 bytes
	(c, off) = rdata(data, off, '<B')
	while c != 0:
		font += chr(c)
		(c, off) = rdata(data, off, '<B')
	add_iter(hd, 'Font name', font, font_pos, off - font_pos, '%ds' % (off - font_pos))
	# only fill and pen
	# fill ID 0x3 - default (black)?
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_obj_paragraph(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 4
	align_map = {0: 'left', 1: 'right', 2: 'block', 3: 'center', 4: 'full'}
	(align, off) = rdata(data, off, '<B')
	add_iter(hd, 'Alignment', key2txt(align, align_map), off - 1, 1, '<B')
	off += 3
	(line, off) = rdata(data, off, '<f')
	add_iter(hd, 'Line spacing', '%2d%%' % (line * 100), off - 4, 4, '<f')
	ref_map = {1: 'Font'}
	_zmf4_obj_refs(hd, size, data, ref_map)

def add_zmf4_obj_text(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 4
	(data_size, off) = rdata(data, off, '<I')
	add_iter(hd, 'Data size?', data_size, off - 4, 4, '<I')
	off = 0x28
	(para_count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of paragraphs', para_count, off - 4, 4, '<I')
	length = 0
	span_count = 0
	off += 4
	i = 1
	while i <= para_count:
		(count, off) = rdata(data, off, '<I')
		add_iter(hd, 'Spans in paragraph %d' % i, count, off - 4, 4, '<I')
		span_count += count
		(pid, off) = rdata(data, off, '<I')
		add_iter(hd, 'Style of paragraph %d' % i, ref2txt(pid), off - 4, 4, '<I')
		off += 4
		i += 1
	i = 1
	while i <= span_count:
		(count, off) = rdata(data, off, '<I')
		add_iter(hd, 'Length of span %d' % i, count, off - 4, 4, '<I')
		length += 2 * count
		off += 4
		(sid, off) = rdata(data, off, '<I')
		add_iter(hd, 'Font of span %d' % i, ref2txt(sid), off - 4, 4, '<I')
		i += 1
	(text, off) = rdata(data, off, '%ds' % length)
	add_iter(hd, 'Text', unicode(text, 'utf-16le'), off - length, length, '%ds' % length)

def add_zmf4_obj_text_frame(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off = _zmf4_obj_bbox(hd, size, data, off)
	# under && middle baseline == over
	# baseline placement available only for top and bottom alignment
	align_flags = {0x10: 'align middle', 0x20: 'align bottom', 0x1: 'under baseline', 0x2: 'baseline in the middle'}
	default_align = 'align top'
	(align, off) = rdata(data, off, '<B')
	align_str = bflag2txt(align, align_flags)
	if (align & 0x10 == 0) and (align & 0x20 == 0):
		align_str += '/' + default_align
		align_str = align_str.strip('/')
	add_iter(hd, 'Alignment', align_str, off - 1, 1, '<B')
	(placement, off) = rdata(data, off, '<B')
	add_iter(hd, 'Placement type on non-level baseline', placement, off - 1, 1, '<B')
	off += 2
	baseline_end = size - 8 * 3
	baseline_length = baseline_end - off
	add_iter(hd, 'Baseline', '', off, baseline_length, '%ds' % baseline_length)
	_zmf4_curve_data(hd, size, data, off)
	ref_types = {6: 'Text'}
	ref_types.update(shape_ref_types)
	_zmf4_obj_refs(hd, size, data, ref_types)

def add_zmf4_obj_start_group(hd, size, data):
	_zmf4_obj_header(hd, size, data)
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_obj_bitmap(hd, size, data):
	_zmf4_obj_header(hd, size, data)
	if size > 0x28:
		path = ''
		(c, off) = rdata(data, 0x28, '<B')
		while c != 0:
			path += chr(c)
			(c, off) = rdata(data, off, '<B')
		add_iter(hd, 'Path', path, 0x28, len(path) + 1, '%ds' % len(path))

def add_zmf4_obj_guidelines(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	(count, off) = rdata(data, off, '<I')
	add_iter(hd, 'Count', count, off - 4, 4, '<I')
	off += 4
	type_map = {0: 'vertical', 1: 'horizontal', 2: 'vertical page margin', 3: 'horizontal page margin'}
	for i in range(1, count + 1):
		lineiter = add_iter(hd, 'Guideline %d' % i, '', off, 16, '16s')
		(typ, off) = rdata(data, off, '<I')
		add_iter(hd, 'Type', key2txt(typ, type_map), off - 4, 4, '<I', parent=lineiter)
		(pos, off) = rdata(data, off, '<I')
		add_iter(hd, 'Position', pos, off - 4, 4, '<I', parent=lineiter)
		off += 8

def add_zmf4_obj_blend(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	start = off
	(length, off) = rdata(data, off, '<I')
	add_iter(hd, 'Length of data', length, off - 4, 4, '<I')
	off += 4
	(colors, off) = rdata(data, off, '<I')
	add_iter(hd, 'Number of colors', colors, off - 4, 4, '<I')
	off += 4
	(steps, off) = rdata(data, off, '<I')
	add_iter(hd, 'Steps', steps, off - 4, 4, '<I')
	(angle, off) = rdata(data, off, '<f')
	add_iter(hd, 'Angle', '%.2frad' % angle, off - 4, 4, '<f')
	i = 1
	while i <= colors:
		off += 4
		(color, off) = rdata(data, off, '3s')
		add_iter(hd, 'Color %d' % i, d2hex(color), off, 3, '3s')
		off += 5
		(position, off) = rdata(data, off, '<f')
		add_iter(hd, 'Position %d' % i, '%.0f%%' % (100 * position), off - 4, 4, '<f')
		i += 1
	_zmf4_obj_refs(hd, size, data, shape_ref_types)

def add_zmf4_view(hd, size, data):
	off = _zmf4_obj_header(hd, size, data)
	off += 4
	(left, off) = rdata(data, off, '<I')
	add_iter(hd, 'Left', left, off - 4, 4, '<I')
	(top, off) = rdata(data, off, '<I')
	add_iter(hd, 'Top', top, off - 4, 4, '<I')
	(right, off) = rdata(data, off, '<I')
	add_iter(hd, 'Right', right, off - 4, 4, '<I')
	(bottom, off) = rdata(data, off, '<I')
	add_iter(hd, 'Bottom', bottom, off - 4, 4, '<I')
	(page, off) = rdata(data, off, '<I')
	add_iter(hd, 'Page', page, off - 4, 4, '<I')
	start = off
	name = ''
	(c, off) = rdata(data, off, '<H')
	while c != 0 and off < size:
		name += unichr(c)
		(c, off) = rdata(data, off, '<H')
	add_iter(hd, 'Name', name, start, off - start, '%ds' % (off - start))

zmf_ids = {
	'zmf2_header': add_zmf2_header,
	'zmf2_bbox': add_zmf2_bbox,
	'zmf2_bitmap_db': add_zmf2_bitmap_db,
	'zmf2_bitmap_id': add_zmf2_bitmap_id,
	'zmf2_data': add_zmf2_data,
	'zmf2_file': add_zmf2_file,
	'zmf2_character': add_zmf2_character,
	'zmf2_color': add_zmf2_color,
	'zmf2_compressed_file': add_zmf2_compressed_file,
	'zmf2_doc_header': add_zmf2_doc_header,
	'zmf2_doc_dimensions': add_zmf2_doc_dimensions,
	'zmf2_fill': add_zmf2_fill,
	'zmf2_fill_trailer': add_zmf2_fill_trailer,
	'zmf2_group': add_zmf2_group,
	'zmf2_name': add_zmf2_name,
	'zmf2_pen': add_zmf2_pen,
	'zmf2_points': add_zmf2_points,
	'zmf2_polygon': add_zmf2_polygon,
	'zmf2_shadow': add_zmf2_shadow,
	'zmf2_star': add_zmf2_star,
	'zmf2_table': add_zmf2_table,
	'zmf2_obj_header': add_zmf2_obj_header,
	'zmf4_header': add_zmf4_header,
	'zmf4_obj': add_zmf4_obj,
	'zmf4_obj_start_layer': add_zmf4_obj_start_layer,
	'zmf4_obj_doc_settings': add_zmf4_obj_doc_settings,
	'zmf4_obj_bitmap': add_zmf4_obj_bitmap,
	'zmf4_obj_blend': add_zmf4_obj_blend,
	'zmf4_obj_color_palette': add_zmf4_obj_color_palette,
	'zmf4_obj_fill': add_zmf4_obj_fill,
	'zmf4_obj_font': add_zmf4_obj_font,
	'zmf4_obj_guidelines': add_zmf4_obj_guidelines,
	'zmf4_obj_image': add_zmf4_obj_image,
	'zmf4_obj_paragraph': add_zmf4_obj_paragraph,
	'zmf4_obj_pen': add_zmf4_obj_pen,
	'zmf4_obj_arrow': add_zmf4_obj_arrow,
	'zmf4_obj_shadow': add_zmf4_obj_shadow,
	'zmf4_obj_ellipse': add_zmf4_obj_ellipse,
	'zmf4_obj_polygon': add_zmf4_obj_polygon,
	'zmf4_obj_curve': add_zmf4_obj_curve,
	'zmf4_obj_rectangle': add_zmf4_obj_rectangle,
	'zmf4_obj_start_group': add_zmf4_obj_start_group,
	'zmf4_obj_table': add_zmf4_obj_table,
	'zmf4_obj_text': add_zmf4_obj_text,
	'zmf4_obj_text_frame': add_zmf4_obj_text_frame,
	'zmf4_preview_bitmap_data': add_zmf4_preview_bitmap_data,
	'zmf4_view': add_zmf4_view,
}

def zmf2_open(page, data, parent, fname):
	file_map = {
		'BitmapDB.zmf': ZMF2Parser.parse_bitmap_db_doc,
		'TextStyles.zmf': ZMF2Parser.parse_text_styles_doc,
		'Callisto_doc.zmf': ZMF2Parser.parse_doc,
		'Callisto_pages.zmf': ZMF2Parser.parse_pages_doc,
	}
	if fname == 'Header':
		update_pgiter_type(page, 'zmf', 'zmf2_header', parent)
	elif file_map.has_key(fname):
		if data != None:
			parser = ZMF2Parser(data, page, parent, file_map[fname])
			parser.parse()

def zmf4_open(data, page, parent):
	parser = ZMF4Parser(data, page, parent)
	parser.parse()

# vim: set ft=python sts=4 sw=4 noet:
