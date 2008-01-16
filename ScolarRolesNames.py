# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

# DEFINITION DES PERMISSIONS (ET NON PAS DES ROLES !)

# prefix all permissions by "Sco" to group them in Zope management tab

# Attention: si on change ses valeurs, il faut verifier les codes
# DTML qui utilisent directement les chaines de caractères...

ScoChangeFormation = "Sco Change Formation"
ScoEditAllNotes = "Sco Modifier toutes notes"
ScoEditAllEvals = "Sco Modifier toutes les evaluations"

ScoImplement    = "Sco Implement Formation"

ScoAbsChange    = "Sco Change Absences"
ScoEtudChangeAdr   = "Sco Change Etud Address" # changer adresse/photo
ScoEtudChangeGroups = "Sco Change Etud Groups" 
ScoEtudInscrit  = "Sco Inscrire Etud" # aussi pour demissions, diplomes
ScoEtudAddAnnotations = "Sco Etud Add Annotations"
ScoEntrepriseView = "Sco View Entreprises"
ScoEntrepriseChange = "Sco Change Entreprises"

ScoView = 'Sco View' 
ScoEnsView = 'Sco View Ens' # parties visibles par enseignants slt

ScoAdminUsers = 'Sco Administrer utilisateurs'
ScoSuperAdmin = 'Sco Super Admin'

# Roles:
# ScoEns, ScoAdmin
