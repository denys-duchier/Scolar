
-- Inscription des etudiants de GTR1
--  (presents dans la table "promo")
-- au semestre "formsemestre_id"


-- inscription au semestre
INSERT INTO notes_formsemestre_inscription 
	(etudid, formsemestre_id, groupetd, groupetp, groupeanglais, etat)
	SELECT etudid, 'SEM1157', groupetd, groupetp, groupeanglais, 'I'
	FROM promo where anneegtr='GTR1' and etat='I' and formation = 'FI';

-- inscriptions a tous les modules du semestre
INSERT INTO notes_moduleimpl_inscription (moduleimpl_id, etudid) 
	SELECT F.moduleimpl_id, I.etudid 
	FROM  notes_moduleimpl F, notes_formsemestre_inscription I 
	WHERE I.formsemestre_id=F.formsemestre_id and F.formsemestre_id='SEM1157';

-- pour les etudianst demissionnaires oubliés !
INSERT INTO notes_moduleimpl_inscription (moduleimpl_id, etudid) 
  SELECT F.moduleimpl_id, I.etudid 
  FROM  notes_moduleimpl F, notes_formsemestre_inscription I
  WHERE I.formsemestre_id=F.formsemestre_id and F.formsemestre_id='SEM1157'
  and I.etat = 'D';

XXXX  reinscrire 2005_E_13 et 2005_E_16 !!!

-- XXX  Pour les GTR2 semestre 3
INSERT INTO notes_formsemestre_inscription 
	(etudid, formsemestre_id, groupetd, groupetp, groupeanglais, etat)
	SELECT etudid, 'SEM1191', groupetd, groupetp, groupeanglais, 'I'
	FROM promo where anneegtr='GTR2' and etat='I' and formation = 'FI';

INSERT INTO notes_moduleimpl_inscription (moduleimpl_id, etudid) 
	SELECT F.moduleimpl_id, I.etudid 
	FROM  notes_moduleimpl F, notes_formsemestre_inscription I 
	WHERE I.formsemestre_id=F.formsemestre_id and F.formsemestre_id='SEM1191';

stop;
-- XXX Pour LPRT FAP
INSERT INTO notes_formsemestre_inscription 
	(etudid, formsemestre_id, groupetd, groupetp, groupeanglais, etat)
	SELECT etudid, 'SEM1401', groupetd, groupetp, groupeanglais, 'I'
	FROM promo where anneegtr='LPRTFAP' and etat='I' and formation = 'LPRTFAP';

INSERT INTO notes_moduleimpl_inscription (moduleimpl_id, etudid) 
	SELECT F.moduleimpl_id, I.etudid 
	FROM  notes_moduleimpl F, notes_formsemestre_inscription I 
	WHERE I.formsemestre_id=F.formsemestre_id and F.formsemestre_id='SEM1401';

-- XXX Pour les GTR2 APP
INSERT INTO notes_formsemestre_inscription 
	(etudid, formsemestre_id, groupetd, groupetp, groupeanglais, etat)
	SELECT etudid, 'SEM1450', groupetd, groupetp, groupeanglais, 'I'
	FROM promo where anneegtr='GTR2' and etat='I' and formation = 'APP';

INSERT INTO notes_moduleimpl_inscription (moduleimpl_id, etudid) 
	SELECT F.moduleimpl_id, I.etudid 
	FROM  notes_moduleimpl F, notes_formsemestre_inscription I 
	WHERE I.formsemestre_id=F.formsemestre_id and F.formsemestre_id='SEM1450';
