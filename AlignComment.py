''' AlignComment
Adds a new in-line comment to the end of an un-commented line or aligns existing comments to this alignment.
Aligns in-line comment text within a single line or block to the following non-comment text indent
Default end of line alignmnet is to column 80 unless set by the "comment_align_column" setting parameter
set in the sublime-settings file tree.'''
import sublime, sublime_plugin

# Use scan routines from the default supplied comment.py plugin
def advance_to_first_non_white_space_on_line(view, pt):
	while True:
		c = view.substr(pt)
		if c == " " or c == "\t":
			pt += 1
		else:
			break

	return pt

def has_non_white_space_on_line(view, pt):
	while True:
		c = view.substr(pt)
		if c == " " or c == "\t":
			pt += 1
		else:
			return c != "\n"

# Use comment type scan routine from the default supplied comment.py plugin
def build_comment_data(view, pt):
	shell_vars = view.meta_info("shellVariables", pt)
	if not shell_vars:
		return ([], [], "")

	# transform the list of dicts into a single dict
	all_vars = {}
	for v in shell_vars:
		if 'name' in v and 'value' in v:
			all_vars[v['name']] = v['value']

	line_comments = []
	block_comments = []
	inline_comment = ""

	# transform the dict into a single array of valid comments
	suffixes = [""] + ["_" + str(i) for i in range(1, 10)]
	for suffix in suffixes:
		start = all_vars.setdefault("TM_COMMENT_START" + suffix)
		end = all_vars.setdefault("TM_COMMENT_END" + suffix)
		mode = all_vars.setdefault("TM_COMMENT_MODE" + suffix)
		disable_indent = all_vars.setdefault("TM_COMMENT_DISABLE_INDENT" + suffix)

		if start and end:
			block_comments.append((start, end, disable_indent == 'yes'))
			block_comments.append((start.strip(), end.strip(), disable_indent == 'yes'))
		elif start:
			line_comments.append((start, disable_indent == 'yes'))
			line_comments.append((start.strip(), disable_indent == 'yes'))
			if len(inline_comment) == 0:
				inline_comment = start
	return (line_comments, block_comments, inline_comment)

class AlignCommentCommand(sublime_plugin.TextCommand):

	# Checks to see if the current line is just white spaces
	def is_a_blank_line(self, view, comment_data, line_region):
		start_position = advance_to_first_non_white_space_on_line(view, line_region.begin())
		return start_position == line_region.end()

	# Checks to see if the first or first non-white space on the line is one of the defined comment strings
	def starts_with_line_comment(self, view, comment_data, line_region, find_non_white=False):
		(line_comments, block_comments) = comment_data
		if find_non_white:
			start_position = advance_to_first_non_white_space_on_line(view, line_region.begin())
		else:
			start_position = line_region.begin()
		found_line_comment = False
		for c in line_comments:
			(start, disable_indent) = c
			comment_region = sublime.Region(start_position, start_position + len(start))
			if view.substr(comment_region) == start:
				found_line_comment = True
		return found_line_comment

	# Checks to see if the line contains one of the defined comment strings between the first non-white space character and the end
	def has_a_line_comment(self, view, comment_data, line_region):
		(line_comments, block_comments) = comment_data
		start_position = advance_to_first_non_white_space_on_line(view, line_region.begin())
		found_line_comment = False
		for pos in range(start_position, line_region.end()):
			for c in line_comments:
				(start, disable_indent) = c
				comment_region = sublime.Region(pos, pos + len(start))
				if view.substr(comment_region) == start:
					found_line_comment = True
					break
			if found_line_comment:
				break
		return (found_line_comment, pos)

	# Start here
	def run(self, edit):
		# print("Start of analysis")
		# Fetch details of the file's indent parameters (match preferences names). These are things that stay constant as the file changes
		insert_spaces = self.view.settings().get('translate_tabs_to_spaces')
		indent_spaces = self.view.settings().get('tab_size')
		comment_column = self.view.settings().get('comment_align_column')
		# Check to see if not defined, set to a value or if defined as a string, then convert to an int
		if comment_column == None:
			comment_column = 80
		elif isinstance(comment_column, str):
			try:
				comment_column = int(comment_column)
			except ValueError:
				comment_column = 80
				print("aligncomment plugin configuration error. 'comment_align_column' not set to a number. Defaulting to a value of 80")
		# print("Comments to be aligned at column {0:d}".format(comment_column))
		for region in self.view.sel():
			comment_data = build_comment_data(self.view, region.begin())
			# Extract the last element and remove from the comment_data list
			inline_comment = comment_data[-1]
			comment_data = comment_data[:-1]
			if (region.end() != self.view.size() and
					build_comment_data(self.view, region.end())[:-1] != comment_data):
				# region comments are not the same, nothing we can do
				continue

			# If no line comments are defined for the language then exit
			if len(inline_comment) == 0:
				continue

			# Look to see if this is a single line block or one of many blocks
			if len(self.view.lines(region)) == 1:
				region_is_single_line = True
			else:
				region_is_single_line = False

			# We process lines as each lines region (start & end positions) change as each line is processed. Line numbers don't change since lines are not deleted
			# Hence we need to refresh the line before processing
			start_line = self.view.rowcol(region.begin())[0]
			end_line = self.view.rowcol(region.end())[0] + 1
			# print("Processing lines {0:d} to {1:d}".format(start_line, end_line))
			# For each line within the region and for any spanned lines
			for line_number in range(start_line, end_line):
				# Fetch current state of the line
				line_region = self.view.line(self.view.text_point(line_number, 0))

				# For a blank line or one with white spaces only, leave line alone
				if len(line_region) == 0 or self.is_a_blank_line(self.view, comment_data, line_region):
					# print("Is a blank line, so ignore")
					continue

				# For a line that has a comment on the start of the line, ignore
				if self.starts_with_line_comment(self.view, comment_data, line_region, False):
					# print("Starts with a comment at column 0, so ignore")
					continue

				# For a line that starts with a comment
				if self.starts_with_line_comment(self.view, comment_data, line_region, True):
					# print("Starts with a comment")
					start_pos = line_region.begin()
					# Search first non-commented line after the current line until the end of the file
					pos = line_region.end()
					next_line = self.view.line(pos)
					while 1:
						# Find the end of the current line
						pos = next_line.end()
						row_n_col = self.view.rowcol(pos)
						# print ("Pointing at {0:d},{1:d}".format(row_n_col[0], row_n_col[1]))
						# Move down to next row at start of line
						pos = self.view.text_point(row_n_col[0] + 1, 0)
						# Check to see if we have run off the end of the file
						if pos >= self.view.size():
							break
						# Pull in the next line
						next_line = self.view.line(pos)
						# print(self.view.substr(next_line))
						if has_non_white_space_on_line(self.view, pos) and not(self.starts_with_line_comment(self.view, comment_data, next_line, True)):
							break
					# Check to see if we have run off the end of the buffer
					if pos < self.view.size():
						# If not, then extract the indent of the next line
						pos = advance_to_first_non_white_space_on_line(self.view, pos)
						# Calculate or count the indent of the non-comment line, since the presence of spces in tabs throws the calculation method out
						if insert_spaces:
							# This is a straight calculation
							row_n_col = self.view.rowcol(pos)
							next_indent = row_n_col[1]
						else:
							non_comment_start = next_line.begin()
							next_indent = 0
							# Count the number of tab characters
							for loc in range(non_comment_start, pos):
								if self.view.substr(loc) == '\t':
									next_indent += 1
						# print("for line '{0:s}' using line '{1:s}' wth indent at column {2:d}".format(self.view.substr(line_region), self.view.substr(next_line), next_indent))
					else:
						# We have run off the end of the file, so set indent to zero
						next_indent = 0
					# print("Is entirely line comment, so align to following line indent at position {0:d}".format(next_indent))
					# Remove any existing indents, these could be mixed tabs and spaces, which cause all sorts of complex code to handle, simpler to just start again
					pos = advance_to_first_non_white_space_on_line(self.view, start_pos)
					# print("Removing region between {0:d} and {1:d} and insering {2:d} spaces/tabs".format(start_pos, pos, next_indent))
					if pos != start_pos:
						remove_region = sublime.Region(start_pos, pos)
						self.view.erase(edit, remove_region)
					# Now add new indents to match next line - not assumes all tabs if buffer is using tabs
					if insert_spaces:
						# Add n spaces
						self.view.insert(edit, start_pos, " "* next_indent)
					else:
						# add n tabs
						self.view.insert(edit, start_pos, "\t"* next_indent)
					continue

				# If the line has a comment, then try to align to the configured comment_column value
				# Values returned are whether there is a comment and where in the line it is
				(has_a_comment, pos) = self.has_a_line_comment(self.view, comment_data, line_region)
				if has_a_comment:
					# print("Line has a comment, so align")
					line_start_tabs = 0
					# print("Has text followed by a comment")
					# Save pos location to give the location of the comment
					comment_buffer_location = pos
					# Now work out if the comment is at the right place or not - it's a pain as a tab = indent_spaces for 1 character in the buffer
					# Logic doesn't cope with all combinations, but as we are replacing like with like it doesn't really matter
					row_n_col = self.view.rowcol(pos)
					line_comment_column = row_n_col[1]
					start_pos = line_region.begin()
					if not(insert_spaces):
						# Count the number of tabs at the start of the line and add that to the end of line column to account for the way columns work with tabs
						pos = advance_to_first_non_white_space_on_line(self.view, start_pos)
						pos -= start_pos
						line_start_tabs = pos
						line_comment_column += (line_start_tabs * (indent_spaces - 1))
						# Count the number of spaces and tabs after the text but before the comment
						remove_spaces = 0
						remove_tabs = 0
						pos = comment_buffer_location - 1
						while (self.view.substr(pos) == " " or self.view.substr(pos) == "\t"):
							if self.view.substr(pos) == " ":
								remove_spaces += 1
							else:
								remove_tabs += 1
							pos -= 1
						line_end_column = self.view.rowcol(pos)[1] + 1
						line_end_column += (line_start_tabs * (indent_spaces - 1))
						first_tab_size = indent_spaces - ((line_end_column) % indent_spaces)
						# print("Currently pointing to character '{0:s}'. Found end of text at column {1:d}. First tab size is {2:d} with {3:d} tabs and {4:d} spaces after".format(
						#	self.view.substr(pos), line_end_column, first_tab_size, remove_tabs, remove_spaces))
						line_comment_column = line_end_column
						line_comment_column += first_tab_size
						line_comment_column += ((remove_tabs - 1) * indent_spaces)
						line_comment_column += remove_spaces
					# print("Comment now at column {0:d}".format(line_comment_column))
					# Subtract one as we have a line termination character on the end
					indent_difference = (comment_column - line_comment_column - 1)
					if indent_difference == 0:
						# print("Comment at correct alignment, so leave where it is")
						continue

					# If we insert tabs, We should remove any tabs or spaces before the comment
					remove_spaces = 0
					pos = comment_buffer_location - 1
					# print("Currently pointing to character '{0:s}'".format(self.view.substr(pos)))
					while (self.view.substr(pos) == " " or self.view.substr(pos) == "\t"):
						remove_spaces += 1
						pos -= 1
					# Now remove the spaces region
					remove_region = sublime.Region(pos + 1, comment_buffer_location)
					self.view.erase(edit, remove_region)
					# print("Found and removed {0:d} spaces before the comment".format(remove_spaces))
					# print("Comment placed at column {0:d} before removal".format(line_comment_column))
					# line_comment_column -= remove_spaces
					line_comment_column = self.view.rowcol(pos)[1] + 1
					if not(insert_spaces):
						line_comment_column += (line_start_tabs * (indent_spaces - 1))
					# print("Comment now at column {0:d}".format(line_comment_column))
					indent_difference = (comment_column - line_comment_column - 1)
					if indent_difference < 1:
						# print("Adding an extra space since indent_difference is {0:d}".format(indent_difference))
						indent_difference = 1
					if insert_spaces:
						insert_text = " " * indent_difference
					else:
						# Adding the first tab takes us to position (n * indent_spaces), then work out the number of full tabs then pad with spaces to configured column
						first_tab_size = indent_spaces - ((line_comment_column) % indent_spaces)
						add_tabs = (indent_difference - first_tab_size) //  indent_spaces
						add_spaces = indent_difference - first_tab_size - (add_tabs * indent_spaces)
						# print("Which is constructed from first tab of {0:d} spaces, {1:d} tab(s) of {2:d} spaces and {3:d} space(s)".format(first_tab_size, add_tabs, indent_spaces, add_spaces))
						# Check to see if the comment to be inserted has a trailing space
						insert_text = "\t" + ("\t" * add_tabs) + (" " * add_spaces  )
					self.view.insert(edit, pos+1, insert_text)
					continue

				# For all other conditions, there is no comment. For mult-line selections, leave line alone
				if not(region_is_single_line):
					# Part of a block, but no comment present, so ignore line
					# print("Has no comment, so ignore")
					continue

				# For no comment and a only a single line is selected/chosen
				# print("Single line that has no comment, so append to the end of the line")
				# Trim any trailing spaces from the line end
				remove_spaces = 0
				# print("Single line so add comment to end of line")
				# Save the current line end position - we will change this if we erase and characters
				line_end_position = line_region.end()
				start_pos = line_region.begin()
				pos = line_end_position - 1
				# print("Currently pointing to character '{0:s}'".format(self.view.substr(pos)))
				while (self.view.substr(pos) == " " or self.view.substr(pos) == "\t"):
					remove_spaces += 1
					pos -= 1
				# Now remove the spaces region
				if remove_spaces != 0:
					remove_region = sublime.Region(pos + 1, line_end_position)
					self.view.erase(edit, remove_region)
					# print("Found and removed {0:d} spaces from the end of the line".format(remove_spaces))
					# Point to new line end since the line in memory is no longer valid
					line_end_position -= remove_spaces
				# Extract the column for the end of the line
				pos = line_end_position
				row_n_col = self.view.rowcol(pos)
				line_end_column = row_n_col[1]
				if not(insert_spaces):
					# Count the number of tabs at the start of the line and add that to the end of line column to account for the way columns work with tabs
					pos = advance_to_first_non_white_space_on_line(self.view, start_pos)
					pos -= start_pos
					line_end_column += (pos * (indent_spaces - 1))
				# print("End of line at column {0:d}".format(line_end_column))
				# Reload the end of the line
				pos = line_end_position
				if line_end_column >= comment_column:
					# After the configured column, so just add a comment to the end
					if insert_spaces:
						# Check to see if the comment to be inserted has a trailing space
						if inline_comment[-1] == " ":
							insert_comment = " " + inline_comment
						else:
							insert_comment = " " + inline_comment + " "
					else:
						# Check to see if the comment to be inserted has a trailing space
						if inline_comment[-1] == " ":
							insert_comment = "\t" + inline_comment
						else:
							insert_comment = "\t" + inline_comment + " "
					self.view.insert(edit, pos, insert_comment)
				else:
					# Subtract one as we have a line termination character on the end
					indent_difference = (comment_column - line_end_column - 1)
					# print("Add {0:d} tabs or spaces to align column {1:d} to column {2:d}".format(indent_difference, line_end_column, comment_column))
					if insert_spaces:
						insert_comment = " " * indent_difference
						# Check to see if the comment to be inserted has a trailing space
						if inline_comment[-1] == " ":
							insert_comment = (" " * indent_difference) + inline_comment
						else:
							insert_comment = (" " * indent_difference) + inline_comment + " "
					else:
						# Adding the first tab takes us to position (n * indent_spaces), then work out the number of full tabs then pad with spaces to configured column
						first_tab_size = indent_spaces - ((line_end_column) % indent_spaces)
						add_tabs = (indent_difference - first_tab_size) //  indent_spaces
						add_spaces = indent_difference - first_tab_size - (add_tabs * indent_spaces)
						# print("Which is constructed from first tab of {0:d} spaces, {1:d} tab(s) of {2:d} spaces and {3:d} space(s)".format(first_tab_size, insert_tabs, indent_spaces, insert_spaces))
						# Check to see if the comment to be inserted has a trailing space
						if inline_comment[-1] == " ":
							insert_comment = "\t" + ("\t" * add_tabs) + (" " * add_spaces) + inline_comment
						else:
							insert_comment = "\t" + ("\t" * add_tabs) + (" " * add_spaces) + inline_comment + " "
					self.view.insert(edit, pos, insert_comment)
				# Place cursor at the end of the line
				self.view.run_command("move_to", {"to": "eol"})

		# print("End of analysis")
# comment_column