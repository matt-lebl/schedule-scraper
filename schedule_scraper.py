# schedule_scraper.py: help plan your UVic courses
# Copyright (C) 2021 Matt Lebl (mlebl@uvic.ca)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import requests
from bs4 import BeautifulSoup as bs
import re
import datetime


class Section:
	def __init__(self, crn, section_code, course_code, time_range, days, location, instructor):
		self.crn = crn

		self.section_code = section_code

		self.course_code = course_code
		
		# use regex to compute start/end times from format like "2:30 PM - 3:50 PM"
		time_re = re.compile(r"(\d\d?):(\d\d) ?([apAP])[mM]? ?- ?(\d\d?):(\d\d) ?([apAP])[mM]?")
		time_match = time_re.match(time_range)
		start_hour = int(time_match.group(1))

		if time_match.group(3).lower() == 'p' and start_hour != 12:
			start_hour += 12
		start_minute = int(time_match.group(2))

		end_hour = int(time_match.group(4))
		if time_match.group(6).lower() == 'p' and end_hour != 12:
			end_hour += 12
		end_minute = int(time_match.group(5))

		self.start_time = datetime.time(hour=start_hour, minute=start_minute)
		self.end_time = datetime.time(hour=end_hour, minute=end_minute)

		self.days = days

		self.location = location
		
		self.instructor = instructor

		self.lock = False

	def __str__(self):
		return "%d %s: %s from %s to %s with %s in %s" % (
			self.crn,
			self.section_code,
			self.days,
			self.start_time.strftime(r"%I:%M %p"),
			self.end_time.strftime(r"%I:%M %p"),
			self.instructor,
			self.location
		)
	
	def __repr__(self):
		return str(self)

	def compatible_with(self, other_section):
		# if they occur on different days, then they are compatible. if they share a day, we need
		# to examine further
		share_days = False
		for day in self.days:
			if day in other_section.days:
				share_days = True
		if share_days == False:
			return True
	
		# disqualify if this section starts during the other section
		if self.start_time >= other_section.start_time and self.start_time <= other_section.end_time:
			return False

		# disqualify if the other section starts during this section
		if other_section.start_time >= self.start_time and other_section.start_time <= self.end_time:
			return False

		# if none of the above, then they are compatible
		return True


class CourseSchedule:
	def __init__(self, course, lecture, lab, tutorial):
		self.course = course
		self.lecture = lecture
		self.lab = lab
		self.tutorial = tutorial
	
	def section_and_crn(self):
		s = "%s" % self.course.code
		if self.lecture is not None:
			s += " %s: [%d] " % (self.lecture.section_code, self.lecture.crn)
		if self.lab is not None:
			s += " %s: [%d] " % (self.lab.section_code, self.lab.crn)
		if self.tutorial is not None:
			s += " %s: [%d] " % (self.tutorial.section_code, self.tutorial.crn)
		return s
	
	def __str__(self):
		s = "%s:" % self.course.code
		if self.lecture is not None:
			s += " %s" % str(self.lecture)
		if self.lab is not None:
			s += " %s" % str(self.lab)
		if self.tutorial is not None:
			s += " %s" % str(self.tutorial)
		return s

	def __repr__(self):
		return str(self)
	
	def compatible_with(self, other_schedule):
		# combine all the components (lecture, lab, and tutorial) into lists so that
		# they are flexible (i.e. easy to compare courses w/ lecture and tutorial components
		# with courses with lecture, lab, tutorial components, etc.
		this_components = []
		other_components = []

		if self.lecture is not None:
			this_components.append(self.lecture)
		if self.lab is not None:
			this_components.append(self.lab)
		if self.tutorial is not None:
			this_components.append(self.tutorial)

		if other_schedule.lecture is not None:
			other_components.append(other_schedule.lecture)
		if other_schedule.lab is not None:
			other_components.append(other_schedule.lab)
		if other_schedule.tutorial is not None:
			other_components.append(other_schedule.tutorial)

		# iterate through both to see if any schedules conflict
		for ours in this_components:
			for theirs in other_components:
				if not ours.compatible_with(theirs):
					# as soon as any two conflict, throw the whole thing out
					return False
		
		# none conflict? they're good.
		return True


class CourseOffering:
	def __init__(self, title, code, lecture_sections, lab_sections, tutorial_sections):
		self.title = title
		self.code = code
		self.lecture_sections = lecture_sections
		self.lab_sections = lab_sections
		self.tutorial_sections = tutorial_sections
		# self.find_self_consistent_combos()

		self.active = True

		self.lecture_locked = False
		self.lab_locked = False
		self.tutorial_locked = False
	
	def find_self_consistent_combos(self):
		lecture_sections = []
		if self.lecture_locked:
			for lecture in self.lecture_sections:
				if lecture.lock:
					lecture_sections = [lecture]
					break
		else:
			lecture_sections = self.lecture_sections

		lab_sections = []
		if self.lab_locked:
			for lab in self.lab_sections: 
				if lab.lock:
					lab_sections = [lab]
		else:
			lab_sections = self.lab_sections

		tutorial_sections = []
		if self.tutorial_locked:
			for tutorial in self.tutorial_sections:
				if tutorial.lock:
					tutorial_sections = [tutorial]
		else:
			tutorial_sections = self.tutorial_sections

		consistent_combos = []
		if not lecture_sections:
			# there are no lecture sections
			if not lab_sections:
				# there are only tutorial sections
				consistent_combos = [CourseSchedule(self, None, None, tut) for tut in tutorial_sections]
			else:
				#there are lab sections
				if not tutorial_sections:
					# there are only lab sections
					consistent_combos = [CourseSchedule(self, None, lab, None) for lab in lab_sections]
				else:
					# there are only lab and tutorial sections
					for lab_section in self.lab_sections:
						for tutorial_section in self.tutorial_sections:
							if lab_section.compatible_with(tutorial_section):
								consistent_combos.append(CourseSchedule(self, None, lab_section, tutorial_section))
		else:
			# there are lecture sections
			if not lab_sections:
				# there are no lab sections
				if not tutorial_sections:
					# there are only lecture sections
					consistent_combos = [CourseSchedule(self, lec, None, None) for lec in lecture_sections]
				else:
					# there are only lecture sections and tutorial sections
					for lecture in lecture_sections:
						for tutorial in tutorial_sections:
							if lecture.compatible_with(tutorial):
								consistent_combos.append(CourseSchedule(self, lecture, None, tutorial))
			else:
				# there are lab sections
				if not tutorial_sections:
					# there are only lecture and lab sections
					for lecture in lecture_sections:
						for lab in lab_sections:
							if lecture.compatible_with(lab):
								consistent_combos.append(CourseSchedule(self, lecture, lab, None))
				else:
					# there are lecture, lab, and tutorial sections
					for lecture in lecture_sections:
						for lab in lab_sections:
							for tutorial in tutorial_sections:
								if lecture.compatible_with(lab):
									if lab.compatible_with(tutorial):
										consistent_combos.append(CourseSchedule(self, lecture, lab, tutorial))
		self.consistent_combos = consistent_combos
				

def earliest_start(schedule):
	return schedule.find_earliest_start()


def latest_end(schedule):
	return schedule.find_latest_end()


def days_off(schedule):
	return schedule.count_days_off()


class CombinedSchedule:
	def __init__(self, course_schedules):
		self.course_schedules = course_schedules
		self.sections = self.condense_sections()
	
	def __str__(self):
		s = ""
		for schedule in self.course_schedules:
			s += "[%s]  " % schedule
		return s
	
	def __repr__(self):
		return str(self)
	
	def condense_sections(self):
		sections = []
		for course_schedule in self.course_schedules:
			if course_schedule.lecture is not None:
				sections.append(course_schedule.lecture)
			if course_schedule.lab is not None:
				sections.append(course_schedule.lab)
			if course_schedule.tutorial is not None:
				sections.append(course_schedule.tutorial)
		return sections

	def find_earliest_start(self):
		earliest = datetime.time(hour=23, minute=59)
		for section in self.sections:
			if section.start_time < earliest:
				earliest = section.start_time
		return earliest

	def find_latest_end(self):
		latest = datetime.time(hour=0, minute=0)
		for section in self.sections:
			if section.end_time > latest:
				latest = section.end_time
		return latest
	
	def count_days_off(self):
		days_off = "mtwrf"
		for section in self.sections:
			for day in section.days:
				days_off = days_off.replace(day.lower(), '')
		return len(days_off)

	def print_calendar(self):

		print("           ┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓")
		print("           ┃ Monday            ┃ Tuesday           ┃ Wednesday         ┃ Thursday          ┃ Friday            ┃")
		print("           ┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩")
		print("           │                   │                   │                   │                   │                   │")

		add_ten = lambda x: datetime.time(hour=x.hour, minute=x.minute + 10) if x.minute + 10 < 60 else datetime.time(hour=x.hour + 1, minute=(x.minute+10)%60)

		current_time = self.find_earliest_start()
		latest_time = self.find_latest_end()

		if not (current_time.minute == 0 or current_time.minute == 30):
			current_time.minute = 0

		while current_time <= latest_time:
			print(" ", end='')

			if current_time.minute == 0 or current_time.minute == 30:
				print("%s" % current_time.strftime(r"%I:%M %p"), end='')
			else:
				print("        ", end='')

			print("  ", end='')

			print("│", end='')
			for day in "mtwrf":
				for section in self.sections:
					if print_schedule_line(day, section, current_time):
						break
				else:
					print(" " * 19, end='')
				print("│", end='')
			print()
			current_time = add_ten(current_time)
		print("           └───────────────────┴───────────────────┴───────────────────┴───────────────────┴───────────────────┘")

						

def print_schedule_line(day, section, current_time):

	if day.lower() not in section.days.lower():
		return False

	add_ten = lambda x: datetime.time(hour=x.hour, minute=x.minute + 10) if x.minute + 10 < 60 else datetime.time(hour=x.hour + 1, minute=(x.minute+10)%60)

	if current_time <= section.start_time and section.start_time < add_ten(current_time):
		print("╭─────────────────╮", end='')
		return True
	elif current_time <= section.end_time and section.end_time < add_ten(current_time):
		print("╰─────────────────╯", end='')
		return True
	elif section.start_time <= current_time and current_time <= section.end_time:
		print("│", end='')
		if add_ten(section.start_time) >= current_time:
			heading = " %s %s" % (section.course_code, section.section_code)
			padding = " " * (17-len(heading))
			print("%s%s" % (heading, padding), end='')
		elif add_ten(add_ten(section.start_time)) >= current_time:
			line = " %s " % section.location[-15:]
			padding = " " * (17-len(line))
			print("%s%s" % (line, padding), end='')
		elif add_ten(add_ten(add_ten(section.start_time))) >= current_time:
			line = " %s " % section.instructor[0:15]
			padding = " " * (17-len(line))
			print("%s%s" % (line, padding), end='')
		elif add_ten(add_ten(add_ten(add_ten(section.start_time)))) >= current_time:
			if section.lock:
				print(" (locked)        ", end='')
			else:
				print(" " * 17, end='')
		else:
			print(" " * 17, end='')
		print("│", end='')
		return True
	return False


def parse_course_from_url(url):
	r = requests.get(url)
	soup = bs(r.text, features="html.parser")
	sections = []
	
	course_title = None
	course_code = None
	
	for caption in soup.find_all('caption'):
		if caption.get_text().strip() == 'Scheduled Meeting Times':
			section_table = caption.parent
			title_string = caption.find_previous(string=re.compile(r".+ - .+ - \S+"))
	
			title_re = re.compile(r"(.+) - (.+) - (.+) - (\S+)")
			m = title_re.search(title_string)
			c_title = m.group(1)
			if course_title == None:
				course_title = c_title
			else:
				if c_title != course_title:
					print("There was an inconsistency in parsing this page. Please ensure it is")
					print("a standard course schedule listing page. Sorry!")
					exit()
			crn = int(m.group(2))
			c_code = m.group(3)
			if course_code == None:
				course_code = c_code
			else:
				if c_code != course_code:
					print("There was an inconsistency in parsing this page. Please ensure it is")
					print("a standard course schedule listing page. Sorry!")
					exit()
			section_code = m.group(4)
	
			rows = section_table.find_all("td")
	
			weeks = rows[0].get_text().strip()
			time_range = rows[1].get_text().strip()
			days = rows[2].get_text().strip()
			location = rows[3].get_text().strip()
			instructor = re.sub(' +', ' ', rows[6].get_text().strip().replace('\n', ''))
			sections.append(Section(crn, section_code, course_code, time_range, days, location, instructor))

	lecture_sections = [section for section in sections if section.section_code.startswith('A')]
	lab_sections = [x for x in sections if x.section_code.startswith('B')]
	tutorial_sections = [x for x in sections if x.section_code.startswith('T')]
	
	return CourseOffering(course_title, course_code, lecture_sections, lab_sections, tutorial_sections)


def print_sections(course):
	print("Lecture Sections:")
	for a in course.lecture_sections:
		print("  %s" % a)
	print("Lab Sections:")
	for b in course.lab_sections:
		print("  %s" % b)
	print("Tutorial Sections:")
	for t in course.tutorial_sections:
		print("  %s" % t)


def find_schedules(courses):
	c = [course for course in courses if course.active == True]
	for course in c:
		course.find_self_consistent_combos()
	possible_schedules = []
	# number of courses under consideration
	num = len(c)
	# number of possible (consistent) schedules for each course under consideration
	lengths = [len(course.consistent_combos) for course in c]
	# which combo of course schedules we are currently considering
	current_indices = [0 for _ in range(num)]
	# which course's schedule index we are incrementing
	index_index = len(current_indices) - 1

	# we start at the end of c (the courses) and increment that course's index (in current_indices)
	# until it reaches its max (as read from lengths) and then we increment the next one to the left
	# and zero it out as well as the ones to the right proceeding through all possible permutations
	# of all the course schedules, accumulating valid ones in possible_schedules

	while True: 
		# compare each of the current schedules to each other discarding the permutation if it has
		# a conflict
		for i in range(num):
			for j in range(num):
				if i <= j:
					continue
				if not c[i].consistent_combos[current_indices[i]].compatible_with(c[j].consistent_combos[current_indices[j]]):
					# print("disqualified conflicting schedule: " + str([c[x].consistent_combos[current_indices[x]] for x in range(num)]))
					break
			# python trick to break out of the inner loop; this else statement is only executed
			# if the for loop completed without a break statement
			else:
				continue

			# if the inner loop broke, this loop will also break to save time.
			break
		# if there was no inner loop break, then this must be a valid schedule
		else:
			possible_schedules.append(CombinedSchedule([c[i].consistent_combos[current_indices[i]] for i in range(num)]))

		index_index = num - 1
		current_indices[index_index] += 1

		
		while current_indices[index_index] >= lengths[index_index]:
			current_indices[index_index] = 0
			index_index -= 1
			if index_index < 0:
				return possible_schedules
			current_indices[index_index] += 1

			

courses = []

print("\n" * 200)

while True:
	print("Please choose an action.")
	print("a - add a course, m - manage courses, f - find schedules, e - exit")
	try:
		action = input("> ")
		print("\n" * 200)
	except EOFError:
		print("Goodbye")
		exit()
	print()

	if action.lower().strip() == 'a':
		url = input("Paste schedule link: ")
		print()
		course = parse_course_from_url(url)
		courses.append(course)
		print("Added %s: %s. Please ensure the following details are correct." % (course.code, course.title))
		print_sections(course)
	elif action.lower().strip() == 'm':
		if len(courses) == 0:
			print("You do not yet have any courses registered! I'll be happy to help you manage")
			print("them after you've registered a course or two. Try using 'a' to add a course.")
			continue

		selected = 0
		while True:
			print("Here are all the courses you've added. Enter a number to select a")
			print("different one, (I have selected the first one for you already), and")
			print("then choose which action you would like to take.")
			print()
			for i in range(len(courses)):
				print("(%d) " % i, end='')
				if i == selected:
					print("-->", end='')
				else:
					print("   ", end='')
				print(" %s: %s (%s)" % (courses[i].code, courses[i].title, "active" if courses[i].active else "inactive"))
			print()
			print("d - delete, a - activate/deactivate, s - list/edit (s)ections, e - exit/back, # - change selected course")
			try:
				action = input("> ")
				print("\n" * 200)
			except EOFError:
				print("Goodbye")
				exit()

			if action.lower().strip() == 'd':
				del courses[selected]
				print("Deleted.")
				print()
				if len(courses) == 0:
					print("Since this was the last remaining course, I'm returning you to the main menu.")
					break
				else:
					selected = 0
			elif action.lower().strip() == 'a':
				courses[selected].active = not courses[selected].active
			elif action.lower().strip() == 's':
				selected_section = 0
				while True:
					print("Viewing %s: %s" % (courses[selected].code, courses[selected].title))
					print("Here is a listing of the sections for this course. You can delete those sections that aren't")
					print("useful to you (perhaps due to an outside obligation or degree restriction) and they will not")
					print("be considered for schedule planning. Be aware, however, that you can't get a section back without")
					print("re-importing the course from the internet. Additionally, you can \"lock\" sections, so that")
					print("the scheduler will only show schedule options with that particular section. You can only lock")
					print("one section at a time from each of the lecture, lab, or tutorial components.")
					num_lecture_sections = len(courses[selected].lecture_sections)
					num_lab_sections = len(courses[selected].lab_sections)
					num_tutorial_sections = len(courses[selected].tutorial_sections)

					if num_lecture_sections == 0 and num_lab_sections == 0 and num_tutorial_sections == 0:
						print("There aren't any sections left in this course! That's one way of deleting the course,")
						print("I suppose. :P I'm going ahead and removing this course for you and returning you to the")
						print("course menu. If you need to add the course again, you can do it from the main menu.")
						del courses[selected]
						selected = 0
						break
					print("Lecture sections:")
					for i in range(num_lecture_sections):
						print("  (%d) " % i, end='')
						if i == selected_section:
							print("-->", end='')
						else:
							print("   ", end='')
						print(" %s" % str(courses[selected].lecture_sections[i]), end='')
						if courses[selected].lecture_sections[i].lock:
							print(" (locked)")
						else:
							print()
					print("Lab sections:")
					for i in range(num_lab_sections):
						print("  (%d) " % (i + num_lecture_sections), end='')
						if i == selected_section - num_lecture_sections:
							print("-->", end='')
						else:
							print("   ", end='')
						print(" %s" % str(courses[selected].lab_sections[i]), end='')
						if courses[selected].lab_sections[i].lock:
							print(" (locked)")
						else:
							print()
					print("Tutorial sections:")
					for i in range(num_tutorial_sections):
						print("  (%d) " % (i + num_lecture_sections + num_lab_sections), end='')
						if i == selected_section - num_lecture_sections - num_lab_sections:
							print("-->", end='')
						else:
							print("   ", end='')
						print(" %s" % str(courses[selected].tutorial_sections[i]), end = '')
						if courses[selected].tutorial_sections[i].lock:
							print(" (locked)")
						else:
							print()

					print()
					print("d - delete, l - lock, e - exit/back, # - change selected section")
					try:
						action = input("> ")
						print("\n" * 200)
					except EOFError:
						print("Goodbye")
						exit()

					if action.lower().strip() == 'd':
						if selected_section < num_lecture_sections:
							if courses[selected].lecture_sections[selected_section].lock:
								courses[selected].lecture_locked = False
							del courses[selected].lecture_sections[selected_section]
						elif selected_section < num_lecture_sections + num_lab_sections:
							if courses[selected].lab_sections[selected_section - num_lecture_sections].lock:
								courses[selected].lab_locked = False
							del courses[selected].lab_sections[selected_section - num_lecture_sections]
						elif selected_section < num_lecture_sections + num_lab_sections + num_tutorial_sections:
							if courses[selected].tutorial_sections[selected_section - num_lecture_sections - num_lab_sections].lock:
								courses[selected].tutorial_locked = False
							del courses[selected].tutorial_sections[selected_section - num_lecture_sections - num_lab_sections]
						selected_section = 0
					elif action.lower().strip() == 'l':
						if selected_section < num_lecture_sections:
							if courses[selected].lecture_sections[selected_section].lock == True:
								courses[selected].lecture_locked = False
								courses[selected].lecture_sections[selected_section].lock = False
							else:
								courses[selected].lecture_locked = True
								for section in courses[selected].lecture_sections:
									section.lock = False
								courses[selected].lecture_sections[selected_section].lock = True
						elif selected_section < num_lecture_sections + num_lab_sections:
							if courses[selected].lab_sections[selected_section - num_lecture_sections].lock == True:
								courses[selected].lab_locked = False
								courses[selected].lab_sections[selected_section - num_lecture_sections].lock = False
							else:
								courses[selected].lab_locked = True
								for section in courses[selected].lab_sections:
									section.lock = False
								courses[selected].lab_sections[selected_section - num_lecture_sections].lock = True
						elif selected_section < num_lecture_sections + num_lab_sections + num_tutorial_sections:
							if courses[selected].tutorial_sections[selected_section - num_lecture_sections - num_lab_sections].lock == True:
								courses[selected].tutorial_locked = False
								courses[selected].tutorial_sections[selected_section - num_lecture_sections - num_lab_sections].lock = False
							else:
								courses[selected].tutorial_locked = True
								for section in courses[selected].tutorial_sections:
									section.lock = False
								courses[selected].tutorial_sections[selected_section - num_lecture_sections - num_lab_sections].lock = True
					elif action.lower().strip() == 'e':
						break
					else:
						try:
							num = int(action)
						except:
							print("Sorry, I didn't understand that.")
							continue

						if num >= num_lecture_sections + num_lab_sections + num_tutorial_sections or num < 0:
							print("Sorry, this has to be one of the presented options.")
							continue

						selected_section = num

				if len(courses) == 0:
					print("Wait, there are no more courses? In this case, I'm returning you to the main menu.")
					break

					
			elif action.lower().strip() == 'e':
				break
			else:
				try:
					num = int(action)
				except:
					print("Sorry, I didn't understand that.")
					print("\n" * 200)
					continue

				if num >= len(courses) or num < 0:
					print("Sorry, this has to be one of the presented options.")
					print("\n" * 200)
					continue

				selected = num
				
	elif action.lower().strip() == 'e':
		print("Goodbye")
		exit()
	elif action.lower().strip() == 'f':
		if len(courses) < 1:
			print("You have not added any courses yet! I'll be happy to work out some schedules for you after")
			print("you add some courses using 'a'.")
			continue
		schedules = find_schedules(courses)
		print("I found %d possible schedules." % len(schedules))
		if len(schedules) == 0:
			print("Sorry about that! If you have sections locked, try unlocking them. Also, you can try")
			print("deactivating some courses to see what schedules you could get if those courses were")
			print("not included.")
			continue
		latest_start_time = datetime.time(hour=0, minute=0)
		earliest_finish_time = datetime.time(hour=23, minute=59)
		num_with_dayoff = 0
		for schedule in schedules:
			if schedule.find_earliest_start() > latest_start_time:
				latest_start_time = schedule.find_earliest_start()
			if schedule.find_latest_end() < earliest_finish_time:
				earliest_finish_time = schedule.find_latest_end()
			if schedule.count_days_off() > 0:
				num_with_dayoff += 1
		print("Latest possible start time: %s" % latest_start_time.strftime(r"%I:%M %p"))
		print("Earliest possible finish time: %s" % earliest_finish_time.strftime(r"%I:%M %p"))
		print("Number of schedules with at least one day off: %d" % num_with_dayoff)
		print()

		while True:
			print("How would you like to sort the possible schedules?")
			print("You can sort by multiple criteria by sorting in order from least important")
			print("to most. For instance, if I kinda want to end my day earlier but I mostly")
			print("want to start my day later, then I'd first sort by earliest finishing time")
			print("and then by latest start time.")
			print()
			print("When you are ready to read through the schedules, use the \"go\" option.")
			print("l - latest start times first")
			print("f - earliest finishing times first")
			print("d - days off first")
			print("g - go, view the schedules")
			print("e - exit/back")

			try:
				action = input("> ")
				print("\n" * 200)
			except EOFError:
				print("Goodbye")
				exit()

			if action.lower().strip() == 'l':
				schedules = sorted(schedules, key=earliest_start, reverse=True)
				print("Sorted the schedules by latest start time.")
			elif action.lower().strip() == 'f':
				schedules = sorted(schedules, key=latest_end)
				print("Sorted the schedules by earliest finish time.")
			elif action.lower().strip() == 'd':
				schedules = sorted(schedules, key=days_off, reverse=True)
				print("Sorted the schedules by days off.")
			elif action.lower().strip() == 'e':
				break
			elif action.lower().strip() == 'g':
				selected = 0
				while True:
					schedules[selected].print_calendar()
					for course_schedule in schedules[selected].course_schedules:
						print(course_schedule.section_and_crn())
					print("Viewing schedule (%d of %d)" % (selected + 1, len(schedules)))
					print("n - next, b - back, e - exit")
					try:
						action = input("> ")
						print("\n" * 200)
					except EOFError:
						print("Goodbye")
						exit()

					if action.lower().strip() == 'n':
						selected = (selected + 1) % len(schedules)
					elif action.lower().strip() == 'b':
						selected = (selected - 1) % len(schedules)
					elif action.lower().strip() == 'e':
						break

	else:
		print("Sorry, I don't know what that means.")


