try:
	from Products.ZBabel import ZBabelTag
except:

	from DocumentTemplate.DT_String import String
	from DocumentTemplate.DT_Util   import render_blocks, Eval, ParseError
	import string, zLOG


	# fake Babel/Fish Tags

	class ZBabelTag:
		'''ZBabel Tag class - The cool translation tag'''

		# define the name of the tag; also tell the system it is a doublet
		name = 'babel'
		blockContinuations = ()


		def __init__(self, blocks):
			'''__init__(self, blocks) --> Initialize tag object; return None'''
			(tname, args, section,) = blocks[0]

			self.section = section


		def render(self, md):
			'''render(self, md) --> Do the Translation; return string'''
			return render_blocks(self.section.blocks, md)
		__call__=render
	# register the DTML-BABEL tag
	String.commands['babel'] = ZBabelTag

	class FishTag:
		'''Fish Tag class - Short-Cut version of the cool translation tag (babel)

		   This tag is used to quickly translate menu-like text snippets, similar to
		   the KDE translation.'''

		# define the tag name
		name = 'fish'

		# define additional variables
		literal = 1

		src = 'label'
		attrs = {'dst': None, 'label': '', 'data': None, 'towerId': None}

		def __init__(self, args):
			'''__init__(self, blocks) --> Initialize tag object; return None'''
			self.section = None
			args = parseTagParameters(args, tag=self.name)
			self.args = self.validateArguments(args)
			
			for attr in self.attrs.keys(): 
				setattr(self, attr, self.attrs[attr])
				
		def validateArguments(self, args):
			'''validateArguments(self, args) --> try to evaluate the passed expression or try to get an object from the passed id; if all this fails, leave the string, it is probably cool!; return tuple of (name, value)'''
			# I stole this from dtml-let...
			# SR: Like he said: Always copy existing code to make you life easier (evben though
			#	  I changed some variables around
			for count in range(len(args)):
				(name, expr,) = args[count]
				if ((expr[:1] == '"') and ((expr[-1:] == '"') and (len(expr) > 1))):
					expr = expr[1:-1]
					try:

						args[count] = (name, Eval(expr).eval)

					except SyntaxError, v:
						(m, (huh, l, c, src,),) = v
						raise ParseError, (('<strong>Expression (Python) Syntax error</strong>:' +
											'<pre>\012%s\012</pre>\012' % v[0]), 'babel')

				elif ((expr[:1] == "'") and ((expr[-1:] == "'") and (len(expr) > 1))):
					expr = expr[1:-1]
					args[count] = (name, expr)

			return args
			
		def render(self, md):
			'''render(self, md) --> Do the Translation; return string'''
			data = None
			for name, expr in self.args:
				if type(expr) is type(''):
					try:
						data = md[expr]
					except:
						data = expr
				else:
					data = expr(md)
					
				#zLOG.LOG("exUserFolder", zLOG.INFO, "rendering name=%s expr=%s data=%s"%(name,expr,data))
				
			print data
			return str(data)
					  	 
		__call__=render


	# register the DTML-FISH tag
	String.commands['fish'] = FishTag



try:
	import re
	parmre=re.compile('''([\000- ]*([^\000- ="']+)=([^\000- ="']+))''');#"))
	dqparmre=re.compile('([\000- ]*([^\000- ="]+)="([^"]*)")')
	sqparmre=re.compile('''([\000- ]*([^\000- =']+)='([^']*)')''')
except:
	import regex
	parmre=regex.compile('''([\000- ]*([^\000- ="']+)=([^\000- ="']+))''');#"))
 	dqparmre=regex.compile('([\000- ]*([^\000- ="]+)="([^"]*)")')
 	sqparmre=regex.compile('''([\000- ]*([^\000- =']+)='([^']*)')''')
	


def parseTagParameters(paramText, result = None, tag = 'babel',
					   parmre=parmre,
					   dqparmre=dqparmre,
					   sqparmre=sqparmre,
					   **parms):
	result = (result or [])

	parsedParam	  = parmre.match(paramText)
	dqParsedParam = dqparmre.match(paramText)
	sqParsedParam = sqparmre.match(paramText)

	# Parse parameters of the form: name=value
	if parsedParam is not None:
		name   = parsedParam.group(2)
		value  = parsedParam.group(3)
		length = len(parsedParam.group(1))

	# Parse parameters of the form: name="value"
	elif dqParsedParam is not None:
		name = dqParsedParam.group(2)
		value = ('"%s"' % dqParsedParam.group(3))
		length = len(dqParsedParam.group(1))

	# Parse parameters of the form: name='value'
	elif sqParsedParam is not None:
		name = sqParsedParam.group(2)
		value = ('''"'%s'"''' % sqParsedParam.group(3))
		length = len(sqParsedParam.group(1))

	else:
		# There are no more parameters to parse
		if ((not paramText) or (not string.strip(paramText))):
			return result
		raise ParseError, (('invalid parameter: "%s"' % paramText), tag)

	# add the parameter/value pait to the results
	result.append((name, value))

	# remove the found parameter from the paramText
	paramText = string.strip(paramText[length:])

	if paramText:
		return apply(parseTagParameters, (paramText, result, tag), parms)
	else:
		return result
