# -*- mode: python -*-
# -*- coding: iso8859-15 -*-


"""Simple form generator/validator

   E. Viennet 2005 - 2008

   v 1.2
"""

from types import *

def TrivialFormulator(form_url, values, formdescription=(), initvalues={},
                      method='post', enctype=None,
                      submitlabel='OK',
                      name=None,
                      formid='tf',
                      cssclass=None,
                      cancelbutton=None,
                      submitbutton=True,
                      submitbuttonattributes=[],
                      top_buttons = False, # place buttons at top of form
                      bottom_buttons=True, # buttons after form
                      readonly=False,
                      is_submitted=False ):
    """
    form_url : URL for this form
    initvalues : dict giving default values
    values : dict with all HTML form variables (may start empty)
    is_submitted:  handle form as if already submitted

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
          convert_numbers: covert int and float values (from string)
          allowed_values : list of possible values (default: any value)
          validator : function validating the field (called with (value,field)).
          max_value : maximum value (for floats and ints)
          explanation: text string to display next the input widget
          withcheckbox: if true, place a checkbox at the left of the input
                        elem. Checked items will be returned in 'tf-checked'
          attributes: a liste of strings to put in the HTML element
          template: HTML template for element 
          HTML elements:
             input_type : 'text', 'textarea', 'password',
                          'radio', 'menu', 'checkbox',
                          'hidden', 'separator', 'file', 'date', 'boolcheckbox',
                          'text_suggest'
                         (default text)
             size : text field width
             rows, cols: textarea geometry
             labels : labels for radio or menu lists (associated to allowed_values)
             vertical: for checkbox; if true, vertical layout
          To use text_suggest elements, one must:
            - specify options in text_suggest_options (a dict)
            - HTML page must load JS AutoSuggest_js and CSS autosuggest_inquisitor_css
            - bodyOnLoad must call JS function init_tf_form(formid)
    """
    method = method.lower()
    if method == 'get':
        enctype = None
    t = TF(form_url, values, formdescription, initvalues,
           method, enctype, submitlabel, name, formid, cssclass,
           cancelbutton=cancelbutton,
           submitbutton=submitbutton,
           submitbuttonattributes=submitbuttonattributes,
           top_buttons=top_buttons, bottom_buttons=bottom_buttons,
           readonly=readonly, is_submitted=is_submitted)
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
                 submitbutton=True,
                 submitbuttonattributes=[],
                 top_buttons = False, # place buttons at top of form
                 bottom_buttons=True, # buttons after form
                 readonly=False, is_submitted=False ):
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
        self.submitbutton = submitbutton
        self.submitbuttonattributes = submitbuttonattributes
        self.top_buttons = top_buttons
        self.bottom_buttons = bottom_buttons
        self.readonly = readonly
        self.result = None
        self.is_submitted = is_submitted
        if readonly:
            self.top_buttons = self.bottom_buttons = False
            self.cssclass += ' readonly'
    def submitted(self):
        "true if form has been submitted"
        if self.is_submitted:
            return True
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
        R.append(tf_error_message(msg))
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
            # special case for boolcheckbox
            if descr.get('input_type', None) == 'boolcheckbox' and self.submitted():
                if not self.values.has_key(field):
                    self.values[field] = 0
                else:
                    self.values[field] = 1     
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
                elif descr.get('input_type',None) == 'boolcheckbox':
                    pass
                elif not val in descr['allowed_values']:
                    msg.append("valeur invalide (%s) pour le champ '%s'"
                               % (val,field) )
                    ok = 0
            if descr.has_key('validator'):
                if not descr['validator'](val,field):
                    msg.append("valeur invalide (%s) pour le champ '%s'"
                               % (val,field) )
                    ok = 0
            # boolean checkbox
            if descr.get('input_type', None) == 'boolcheckbox':
                if int(val):
                    self.values[field] = 1
                else:
                    self.values[field] = 0
                # open('/tmp/toto','a').write('checkvalues: val=%s (%s) values[%s] = %s\n' % (val, type(val), field, self.values[field]))
            if descr.get('convert_numbers',False):
                if typ[:3] == 'int':
                    self.values[field] = int(self.values[field])
                elif  typ == 'float' or typ == 'real':   
                    self.values[field] = float(self.values[field].replace(',','.'))
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
        itemtemplate = """<tr%(item_dom_attr)s>
        <td class="tf-fieldlabel">%(label)s</td><td class="tf-field">%(elem)s</td>
        </tr>
        """
        hiddenitemtemplate = "%(elem)s"
        separatortemplate = '<tr><td colspan="2">%(label)s</td></tr>'
        # ---- build form
        buttons_markup = ''
        if self.submitbutton:
            buttons_markup+= ('<input type="submit" name="%s_submit" value="%s" %s>'
                              % (self.formid,self.submitlabel, ' '.join(self.submitbuttonattributes)))
        if self.cancelbutton:
            buttons_markup += (' <input type="submit" name="%s_cancel" value="%s">'
                               % (self.formid,self.cancelbutton))

        R = []
        suggest_js = []
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
        if self.top_buttons:
            R.append(buttons_markup + '<p></p>')
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
            item_dom_id = descr.get('dom_id', '')
            if item_dom_id:
                item_dom_attr = ' id="%s"' % item_dom_id
            else:
                item_dom_attr = ''
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
                lab.append('<input type="checkbox" name="%s:list" value="%s" onclick="tf_enable_elem(this)" %s/>' % ('tf-checked', field, checked ) )
            lab.append(title)
            #
            attribs = ' '.join(descr.get('attributes', []))
            if withcheckbox and not checked: # desactive les element non coches:
                attribs += ' disabled="true"'
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
            elif input_type == 'checkbox' or input_type == 'boolcheckbox':
                if input_type == 'checkbox':                
                    labels = descr.get('labels', descr['allowed_values'])
                else:  # boolcheckbox
                    labels = [ '' ]
                    descr['allowed_values'] = ['1']
                vertical=descr.get('vertical', False)
                if vertical:
                    lem.append('<table>')
                for i in range(len(labels)):
                    if input_type == 'checkbox':
                        #from notes_log import log # debug only
                        #log('checkbox: values[%s] = "%s"' % (field,repr(values[field]) ))
                        #log("descr['allowed_values'][%s] = '%s'" % (i, repr(descr['allowed_values'][i])))
                        if descr['allowed_values'][i] in values[field]:
                            checked='checked="checked"'
                        else:
                            checked=''
                    else: # boolcheckbox
                        #open('/tmp/toto','a').write('GenForm: values[%s] = %s (%s)\n' % (field, values[field], type(values[field])))
                        try:
                            v = int(values[field])
                        except:
                            v = 0
                        if v:
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
            elif input_type == 'date': # JavaScript widget for date input
                if values[field]:
                    cv = ", '%s'" % values[field]
                else:
                    cv = ''
                lem.append("<script>DateInput( '%s', false, 'DD/MM/YYYY' %s )</script>" % (field,cv))
            elif input_type == 'text_suggest':
                lem.append( '<input type="text" name="%s" id="%s" size="%d" %s' % (field,field,size,attribs) )
                lem.append( ('value="%('+field+')s" />') % values )
                suggest_js.append( 
                    """var %s_opts = %s;
                    var %s_as = new bsn.AutoSuggest('%s', %s_opts);
                    """ % (field, dict2js(descr.get('text_suggest_options',{})), field, field, field))
            else:
                raise ValueError('unkown input_type for form (%s)!'%input_type)
            explanation = descr.get('explanation', '')
            if explanation:
                lem.append('<i>%s</i>' % explanation )
            R.append( etempl % { 'label' : '\n'.join(lab),
                                 'elem' : '\n'.join(lem),
                                 'item_dom_attr' : item_dom_attr } )
        R.append( '</table>' )
        
        if self.bottom_buttons:
            R.append( '<br/>' + buttons_markup )
            
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
        if suggest_js:
            # nota: formid is currently ignored 
            # => only one form with text_suggest field on a page.
            R.append("""<script type="text/javascript">
            function init_tf_form(formid) {
                %s
            }
            </script>""" % '\n'.join(suggest_js))
        # Javascript common to all forms:
        R.append("""<script type="text/javascript">
	// controle par la checkbox
	function tf_enable_elem(checkbox) {
	  oid = checkbox.value;
	  if (oid) {
	     elem = document.getElementById(oid)
	     if (elem) {
	         if (checkbox.checked) {
	             elem.disabled = false;
	         } else {
	             elem.disabled = true;
	         }
	     }
	  }
	}        
        </script>""")
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
            if input_type == 'text' or input_type == 'text_suggest':
                R.append( ('%('+field+')s') % values )
            elif input_type in ('radio', 'menu', 'checkbox', 'boolcheckbox'):
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

def dict2js(d):
    """convert Python dict to JS code"""
    r = []
    for k in d:
        v = d[k]
        if type(v) == BooleanType:
            if v:
                v = 'true'
            else:
                v = 'false'
        elif  type(v) == StringType:
            v = '"'+v+'"'
        
        r.append( '%s: %s' % (k,v) )
    return '{' + ',\n'.join(r) + '}'

def tf_error_message(msg):
    """html for form error message"""
    if not msg:
        return ''
    if type(msg) == StringType:
        msg = [msg]
    return '<ul class="tf-msg"><li class="tf-msg">%s</li></ul>' % '</li><li class="tf-msg">'.join(msg)
