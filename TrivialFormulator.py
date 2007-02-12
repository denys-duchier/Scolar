# -*- coding: iso8859-15 -*-


"""Simple form generator/validator

   E. Viennet 2005

   v 1.0
"""

def TrivialFormulator(form_url, values, formdescription=(), initvalues={},
                      method='post', enctype=None,
                      submitlabel='OK', name=None, formid='tf', cssclass=None,
                      cancelbutton=None,
                      readonly=False ):
    """
    form_url : URL for this form
    initvalues : dict giving default values
    values : dict with all HTML form variables (may start empty)
    Returns (status, HTML form, values)
         status = 0 (html to display),
                  1 (ok, validated values in "values")
                  -1 cancel (if cancelbutton specified)
         HTML form: html string (form to insert in your web page)
         values: None or, when the form is submitted and correctly filled,
                 a dictionnary with the requeted values.
    formdescription: sequence [ (field, description), ... ]
        where description is a dict with following (optional) keys:
          default    : default value for this field ('')
          title      : text titre (default to field name)
          allow_null : if true, field can be left empty (default true)
          type       : 'string', 'int', 'float' (default to string), 'list' (only for hidden)
          allowed_values : list of possible values (default: any value)
          max_value : maximum value (for floats and ints)
          explanation: text string to display next the input widget
          withcheckbox: if true, place a checkbox at the left of the input
                        elem. Checked items will be returned in 'tf-checked'
          attributes: a liste of strings to put in the HTML element
          HTML elements:
             input_type : 'text', 'textarea', 'password',
                          'radio', 'menu', 'checkbox',
                          'hidden', 'separator', 'file'
                         (default text)
             size : text field width
             rows, cols: textarea geometry
             labels : labels for radio or menu lists (associated to allowed_values)
             vertical: for checkbox; if true, vertical layout
    """
    method = method.lower()
    if method == 'get':
        enctype = None
    t = TF(form_url, values, formdescription, initvalues,
           method, enctype, submitlabel, name, formid, cssclass, cancelbutton, readonly)
    form = t.getform()
    if t.canceled():
        res = -1
    elif t.submitted() and t.result:
        res = 1
    else:
        res = 0
    return res, form, t.result
    
class TF:
    def __init__(self, form_url, values, formdescription=[], initvalues={},
                 method='POST', enctype=None, submitlabel='OK', name=None,
                 formid='tf', cssclass=None,
                 cancelbutton=None,
                 readonly=False ):
        self.form_url = form_url
        self.values = values
        self.formdescription = list(formdescription)
        self.initvalues = initvalues
        self.method = method
        self.enctype = enctype
        self.submitlabel = submitlabel
        self.name = name
        self.formid = formid
        self.cssclass = cssclass
        self.cancelbutton = cancelbutton
        self.readonly = readonly
        self.result = None
    def submitted(self):
        "true if form has been submitted"
        #return self.values.get('%s_submit'%self.formid,False)
        return self.values.get('%s-submitted'%self.formid,False)
    def canceled(self):
        "true if form has been canceled"
        return self.values.get('%s_cancel'%self.formid,False)
    def getform(self):
        "return HTML form"
        R = []
        msg = None
        self.setdefaultvalues()
        if self.submitted() and not self.readonly:
            msg = self.checkvalues()
        # display error message
        if msg:
            R.append('<ul class="tf-msg"><li class="tf-msg">%s</li></ul>'
                     % '</li><li class="tf-msg">'.join(msg))
        # form or view
        if self.readonly:
            R = R + self._ReadOnlyVersion( self.formdescription, self.values )
        else:
            R = R + self._GenForm()
        # 
        return '\n'.join(R)
    __str__ = getform
    __repr__ = getform

    def setdefaultvalues(self):
        "set default values and convert numbers to strings"
        for (field,descr) in self.formdescription:        
            if not self.values.has_key(field):
                if descr.has_key('default'): # first: default in form description
                    self.values[field] = descr['default']
                else:                        # then: use initvalues dict
                    self.values[field] = self.initvalues.get( field, '' )
                if self.values[field] == None:
                    self.values[field] = ''
        # convert numbers
        if type(self.values[field]) == type(1) or type(self.values[field]) == type(1.0):
            self.values[field] = str(self.values[field])
        #
        if not self.values.has_key('tf-checked'):
            if self.submitted():
                # si rien n'est coché, tf-checked n'existe plus dans la reponse
                self.values['tf-checked'] = []
            else:
                self.values['tf-checked'] = self.initvalues.get( 'tf-checked', [] )
        self.values['tf-checked'] = [ str(x) for x in self.values['tf-checked'] ]

    def checkvalues(self):
        "check values. Store .result and returns msg"
        ok = 1
        msg = []
        for (field,descr) in self.formdescription:
            val   = self.values[field]
            # do not check "unckecked" items
            if descr.get('withcheckbox', False):
                if not field in self.values['tf-checked']:
                    continue
            # null values
            allow_null = descr.get('allow_null',True)
            if not allow_null:
                if val == '' or val == None:
                    msg.append("Le champ '%s' doit être renseigné"
                               % descr.get('title', field))
                    ok = 0
            # type
            typ = descr.get('type', 'string')
            if val != '' and val != None:
                # check only non-null values
                if typ[:3] == 'int':
                    try:
                        val = int(val)
                        if descr.has_key('max_value') and val > descr['max_value']:
                            msg.append("La valeur (%d) du champ '%s' est trop grande (max=%s)"
                                       % (val,field,descr['max_value']))
                            ok = 0
                    except:
                        msg.append(
                            "La valeur du champ '%s' doit être un nombre entier" % field )
                        ok = 0
                elif typ == 'float' or typ == 'real':                
                    self.values[field] = self.values[field].replace(',','.')
                    try:                        
                        val = float(val.replace(',','.')) # allow ,
                        if descr.has_key('max_value') and val > descr['max_value']:
                            msg.append("La valeur (%f) du champ '%s' est trop grande (max=%s)"
                                       % (val,field,descr['max_value']))
                            ok = 0
                    except:
                        msg.append("La valeur du champ '%s' doit être un nombre" % field )
                        ok = 0
            # allowed values
            if descr.has_key('allowed_values'):
                if descr.get('input_type',None) == 'checkbox':
                    # for checkboxes, val is a list
                    for v in val:
                        if not v in descr['allowed_values']:
                            msg.append("valeur invalide (%s) pour le champ '%s'" % (val,field) )
                            ok = 0
                elif not val in descr['allowed_values']:
                    msg.append("valeur invalide (%s) pour le champ '%s'"
                               % (val,field) )
                    ok = 0
        if ok:            
            self.result = self.values            
        else:
            self.result = None
        return msg


    def _GenForm(self, cssclass=None, method='',
                 enctype=None, form_url='' ):
        values = self.values
        add_no_enter_js = False # add JS function to prevent 'enter' -> submit
        # form template
        # xxx
        # default template for each input element
        itemtemplate = """<tr>
        <td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s</td>
        </tr>
        """
        hiddenitemtemplate = "%(elem)s"
        separatortemplate = '<tr><td colspan="2">%(label)s</td></tr>'
        # ---- build form
        R = []
        if self.enctype is None:
            if self.method == 'post':
                enctype = 'multipart/form-data'
            else:
                enctype = 'application/x-www-form-urlencoded'
        if self.cssclass:
            klass = ' class="%s"' % self.cssclass
        else:
            klass = ''
        if self.name:
            name = self.name
        else:
            name = 'tf'
        R.append( '<form action="%s" method="%s" id="%s" enctype="%s" name="%s" %s>'
                  % (self.form_url,self.method,self.formid,enctype,name,klass) )
        R.append('<input type="hidden" name="%s-submitted" value="1"/>'%self.formid)
        R.append( '<table>')
        idx = 0
        for idx in range(len(self.formdescription)):
            (field,descr) = self.formdescription[idx]
            nextitemname = None
            if idx < len(self.formdescription) - 2:
                nextitemname = self.formdescription[idx+1][0]
            size = descr.get('size', 12)
            rows = descr.get('rows',  5)
            cols = descr.get('cols', 60)
            title= descr.get('title', field.capitalize())
            withcheckbox =  descr.get('withcheckbox', False )
            input_type = descr.get('input_type', 'text')
            # choix du template
            etempl= descr.get('template', None)
            if etempl is None:
                if input_type == 'hidden':
                    etempl = hiddenitemtemplate
                elif input_type == 'separator':
                    etempl = separatortemplate
                    R.append( etempl % { 'label' : title } )
                    continue
                else:
                    etempl = itemtemplate
            lab = []
            lem = []
            if withcheckbox and input_type != 'hidden':
                if field in values['tf-checked']:
                    checked='checked="checked"'
                else:
                    checked=''
                lab.append('<input type="checkbox" name="%s:list" value="%s" %s/>' % ('tf-checked', field, checked ) )
            lab.append(title)
            #
            attribs = ' '.join(descr.get('attributes', []))
            #
            if input_type == 'text':
                lem.append( '<input type="text" name="%s" size="%d" %s' % (field,size,attribs) )
                if descr.get('return_focus_next',False): # and nextitemname:
                    # JS code to focus on next element on 'enter' key
                    # ceci ne marche que pour desactiver enter sous IE (pas Firefox)
                    # lem.append('''onKeyDown="if(event.keyCode==13){
                    # event.cancelBubble = true; event.returnValue = false;}"''')
                    lem.append('onkeypress="return enter_focus_next(this, event);"')
                    add_no_enter_js = True
#                    lem.append('onchange="document.%s.%s.focus()"'%(name,nextitemname))
#                    lem.append('onblur="document.%s.%s.focus()"'%(name,nextitemname))
                lem.append( ('value="%('+field+')s" />') % values )
            elif input_type == 'password':
                lem.append( '<input type="password" name="%s" size="%d" %s' % (field,size,attribs) )
                lem.append( ('value="%('+field+')s" />') % values )
            elif input_type == 'radio':
                labels = descr.get('labels', descr['allowed_values'])
                for i in range(len(labels)):
                    if descr['allowed_values'][i] == values[field]:
                        checked='checked="checked"'
                    else:
                        checked=''
                    lem.append(
                        '<input type="radio" name="%s" value="%s" %s %s>%s</input>'
                        % (field, descr['allowed_values'][i], checked, attribs, labels[i]) )
            elif input_type == 'menu':
                lem.append('<select name="%s" %s>'%(field,attribs))
                labels = descr.get('labels', descr['allowed_values'])
                for i in range(len(labels)):
                    if str(descr['allowed_values'][i]) == str(values[field]):
                        selected='selected'
                    else:
                        selected=''
                    lem.append('<option value="%s" %s>%s</option>'
                               %(descr['allowed_values'][i],selected,labels[i]) )
                lem.append('</select>')
            elif input_type == 'checkbox':
                labels = descr.get('labels', descr['allowed_values'])
                vertical=descr.get('vertical', False)
                if vertical:
                    lem.append('<table>')
                for i in range(len(labels)):
                    if descr['allowed_values'][i] in values[field]:
                        checked='checked="checked"'
                    else:
                        checked=''
                    if vertical:
                        lem.append('<tr><td>')
                    lem.append('<input type="checkbox" name="%s:list" value="%s" %s %s>%s</input>'
                               % (field, descr['allowed_values'][i], attribs, checked, labels[i]) )
                    if vertical:
                        lem.append('</tr></td>')
                if vertical:
                    lem.append('</table>')
            elif input_type == 'textarea':
                lem.append('<textarea name="%s" rows="%d" cols="%d" %s>%s</textarea>'
                           % (field,rows,cols,attribs,values[field]) )
            elif input_type == 'hidden':
                if descr.get('type','') == 'list':
                    for v in values[field]:
                        lem.append('<input type="hidden" name="%s:list" value="%s" %s />' % (field,v,attribs))
                else:
                    lem.append('<input type="hidden" name="%s" value="%s" %s />' % (field,values[field],attribs))
            elif input_type == 'separator':
                pass
            elif input_type == 'file':
                lem.append('<input type="file" name="%s" size="%s" value="%s" %s/>' % (field,size,values[field], attribs))
            else:
                raise ValueError('unkown input_type for form (%s)!'%input_type)
            explanation = descr.get('explanation', '')
            if explanation:
                lem.append('<i>%s</i>' % explanation )
            R.append( etempl % { 'label' : '\n'.join(lab),
                                 'elem' : '\n'.join(lem) } )
        R.append( '</table>' )
        R.append('<br/><input type="submit" name="%s_submit" value="%s">'
                 % (self.formid,self.submitlabel) )
        if self.cancelbutton:
            R.append('<input type="submit" name="%s_cancel" value="%s">'
                     % (self.formid,self.cancelbutton))
        if add_no_enter_js:
            R.append("""<script type="text/javascript">
            function enter_focus_next (elem, event) {
		var cod = event.keyCode ? event.keyCode : event.which ? event.which : event.charCode;
                enter = false;
                if (event.keyCode == 13)
                    enter = true;
                if (event.which == 13)
                    enter = true;
                if (event.charCode == 13)
                    enter = true;
		if (enter) {
			var i;
			for (i = 0; i < elem.form.elements.length; i++)
				if (elem == elem.form.elements[i])
					break;
                        if (i < (elem.form.elements.length-3)) 
                            elem.form.elements[i+1].focus();
			return false;
		} 
		else
		   return true;
	}</script>
            """) # enter_focus_next ignore 2 boutons a la fin (ok, cancel)
        R.append('</form>')
        return R
    
    
    def _ReadOnlyVersion(self, formdescription, values ):
        "Generate HTML for read-only view of the form"
        R = ['<table>']
        for (field,descr) in formdescription:
            title= descr.get('title', field.capitalize())
            withcheckbox =  descr.get('withcheckbox', False )
            input_type = descr.get('input_type', 'text')
            if input_type != 'hidden':
                R.append( '<tr>')
                if input_type == 'separator': # separator
                    R.append('<td colspan="2">%s</td></tr>' % title )
                    continue
                R.append( '<td class="tf-ro-fieldlabel">' )
                R.append( '%s</td>' % title )
                R.append( '<td class="tf-ro-field">' )
            if input_type == 'text':
                R.append( ('%('+field+')s') % values )
            elif input_type in ('radio', 'menu', 'checkbox'):
                labels = descr.get('labels', descr['allowed_values'])
                for i in range(len(labels)):
                    if descr['allowed_values'][i] == values[field]:
                        R.append('%s' % labels[i])
            elif input_type == 'textarea':
                R.append( '<p>%s</p>' % values[field] )
            elif input_type == 'separator' or  input_type == 'hidden':
                pass
            elif input_type == 'file':
                R.append( "'%s'" % values[field] )
            else:
                raise ValueError('unkown input_type for form (%s)!'%input_type)
            if input_type != 'hidden':
                R.append( '</td></tr>' )
        R.append( '</table>' )
        return R

