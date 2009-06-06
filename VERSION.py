# -*- mode: python -*-
# -*- coding: iso8859-15 -*-

SCOVERSION = "6.0"

SCONAME = "ScoDoc"

SCONEWS = """

<h4>Juin 2009</h4>
<ul>
<li>Corrections et améliorations diverses</h4>
</ul>

<h4>Juillet 2008: version 6.0</h4>
<ul>
<li>Installeur automatisé pour Linux</li>
<li>Amélioration ergonomie (barre menu pages semestres)</li>
<li>Refonte fiche étudiant (parcours)</li>
<li>Archivage des documents (PV)</li>
<li>Nouvel affichage des notes des évaluations</li>
<li>Nombreuses corrections et améliorations</li>
</ul>

<h4>Juin 2008</h4>
<ul>
<li>Rangs sur les bulletins</li>
</ul>

<h4>Février 2008</h4>
<ul>
<li>Statistiques et suivis de cohortes (chiffres et graphes)</li>
<li>Nombreuses petites corrections suites aux jurys de janvier</li>
</ul>

<h4>Janvier 2008</h4>
<ul>
<li>Personnalisation des régles de calculs notes d'option (sport, culture)</li>
<li>Edition de PV de jury individuel</li>
</ul>

<h4>Novembre 2007</h4>
<ul>
<li>Vérification des absences aux évaluations</li>
<li>Import des photos depuis portail, trombinoscopes en PDF</li>
</ul>

<h4>Septembre 2007</h4>
<ul>
<li>Importation des etudiants depuis étapes Apogée</li>
<li>Inscription de groupes à des modules (options ou parcours)</li>
<li>Listes de étapes Apogée (importées du portail)</li>
</ul>

<h4>Juillet 2007</h4>
<ul>
<li>Import utilisateurs depuis Excel</li>
<li>Nouvelle gestion des passage d'un semestre à l'autre</li>
</ul>

<h4>Juin 2007: version 5.0</h4>
<ul>
<li>Suivi des parcours et règles de décision des jurys DUT</li>
<li>Capitalisation des UEs</li>
<li>Edition des PV de jurys et courriers aux étudiants</li>
<li>Feuilles (excel) pour préparation jurys</li>
<li>Nombreuses petites améliorations</li>
</ul>

<h4>Avril 2007</h4>
<ul>
<li>Paramètres de mise en page des bulletins en PDF</li>
</ul>

<h4>Février 2007</h4>

<ul>
<li>Possibilité de ne <em>pas</em> publier les bulletins sur le portail</li>
<li>Gestion des notes "en attente" (publication d'évaluations sans correction de toutes les copies)</li>
<li>Amélioration formulaire saisie absences, saisie absences par semestre.</li>
</ul>

<h4>Janvier 2007</h4>
<ul>
<li>Possibilité d'initialiser les notes manquantes d'une évaluation</li>
<li>Recupération des codes NIP depuis Apogée</li>
<li>Gestion des compensations inter-semestre DUT (en cours de développement)</li>
<li>Export trombinoscope en archive zip</li>
</ul>

<h4>Octobre 2006</h4>
<ul>
<li>Réorganisation des pages d'accueil</li>
<li>Ajout des "nouvelles" (dernières opérations), avec flux RSS</li>
<li>Import/Export XML des formations, duplication d'une formation (versions)</li>
<li>Bulletins toujours sur une seule feuille (passage à ReportLab 2.0)</li>
<li>Suppression d'un utilisateur</il>
</ul>
<h4>Septembre 2006</h4>
<ul>
<li>Page pour suppression des groupes.</li>
<li>Amélioration gestion des utilisateurs</li>
<li>"Verrouillage" des semestres</li>
<li>Liste d'enseignants (chargés de TD) associés à un module (et pouvant saisir des notes)</li>
<li>Noms de types de groupes (TD, TP, ...) modifiables</li>
<li>Tableau rudimentaire donnant la répartition des bacs dans un semestre</li>
<li>Amélioration mise en page des listes au format excel</li>
<li>Annulation des démissions</li>
</ul>

<h4>Juillet 2006</h4>
<ul>
<li>Dialogue permettant au directeur des études de modifier
les options d'un semestre</li>
<li>Option pour ne pas afficher les UE validées sur les bulletins</li>
</ul>

<h4>30 juin 2006</h4>
<ul>
<li>Option pour ne pas afficher les décisions sur les bulletins</li>
<li>Génération feuilles pour préparation jury</li>
<li>Gestion des modules optionnels</li>
<li>Prise en compte note "activités culturelles ou sportives"</li>
<li>Amélioration tableau de bord semestre</li>
<li>Import listes étudiants depuis Excel (avec code Apogée)</li>
</ul>

<h4>12 juin 2006</h4>
<ul>
<li>Formulaire dynamique d'affectation aux groupes</li>
<li>Tri des tableaux (listes, récapitulatif)</li>
<li>Export XML des infos sur un etudiant et des groupes</li>
</ul>

<h4>12 mai 2006</h4>
<ul>
<li>Possibilité de suppression d'un semestre</li>
<li>Export XML du tableau recapitulatif des notes du semestre</li>
<li>Possibilité de supression d'une formation complète</li>
</ul>

<h4>24 avril 2006</h4>
<ul>
<li>Export bulletins en XML (expérimental)</li>
<li>Flag "gestion_absence" sur les semestres de formation</li>
</ul>

<h4>4 mars 2006</h4>
<ul>
<li>Formulaire d'inscription au semestre suivant.</li>
<li>Format "nombre" dans les feuilles excel exportées.</li>
</ul>

<h4>23 février 2006</h4>
<ul>
<li>Décisions jury sur bulletins.</li>
</ul>

<h4>17 janvier 2006</h4>
<ul>
<li>Ajout et édition d'appréciations sur les bulletins.</li>
</ul>
<h4>12 janvier 2006</h4>
<ul>
<li>Envoi des bulletins en PDF par mail aux étudiants.</li>
</ul>

<h4>6 janvier 2006</h4>
<ul>
<li>Affichage des ex-aequos.</li>
<li>Classeurs bulletins PDF en différentes versions.</li>
<li>Corrigé gestion des notes des démissionnaires.</li>
</ul>

<h4>1er janvier 2006</h4>
<ul>
<li>Import du projet dans Subversion / LIPN.</li>
<li>Lecture des feuilles de notes Excel.</li>
</ul>

<h4>31 décembre 2005</h4>
<ul>
<li>Listes générées au format Excel au lieu de CSV.</li>
<li>Bug fix (création/saisie evals).</li>
</ul>

<h4>29 décembre 2005</h4>
<ul>
<li>Affichage des moyennes de chaque groupe dans tableau de bord module.
</ul>

<h4>26 décembre 2005</h4>
<ul>
<li>Révision inscription/édition <em>individuelle</em> d'étudiants.</li>
<li>Amélioration fiche étudiant (cosmétique, liste formations, actions).</li>
<li>Listings notes d'évaluations anonymes (utilité douteuse ?).</li>
<li>Amélioration formulaire saisie notes ('enter' -> champ suivant).</li>
</ul>

<h4>24 décembre 2005</h4>
<ul>
<li>Génération de bulletins PDF
</li>
<li>Suppression de notes (permet donc de supprimer une évaluation)
</li>
<li>Bulletins en versions courtes (seulement moyennes de chaque module), longues
(toutes les notes) et intermédiaire (moyenne de chaque module plus notes dans les évaluations sélectionnées).
</li>
<li>Notes moyennes sous les barres en rouge dans le tableau récapitulatif (seuil=10 sur la moyenne générale, et 8 sur chaque UE).
</li>
<li>Colonne "groupe de TD" dans le tableau récapitulatif des notes.
</ul>
"""

