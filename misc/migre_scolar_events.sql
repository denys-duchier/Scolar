
-- inscription des GTR1

-- inscrit tous
insert into scolar_events (etudid, event_date, formsemestre_id, event_type)
             SELECT etudid, '2005-09-01', 'SEM1157', 'INSCRIPTION'
             FROM promo where anneegtr='GTR1' and annee=2005 and formation = 'FI';

-- demissionne les D

insert into scolar_events (etudid, event_date, formsemestre_id, event_type)
             SELECT etudid, date_sortie, 'SEM1157', 'DEMISSION'
             FROM promo where anneegtr='GTR1' and annee=2005 and formation = 'FI' and etat='D';


-------- GTR2 FI
insert into scolar_events (etudid, event_date, formsemestre_id, event_type)
SELECT etudid, '2005-09-01', 'SEM1191', 'INSCRIPTION' FROM promo where anneegtr='GTR2' and annee=2005 and formation = 'FI';
-- (pas de demissionnaires)


---- GTR2 APP
insert into scolar_events (etudid, event_date, formsemestre_id, event_type)
SELECT etudid, '2005-10-01', 'SEM1450', 'INSCRIPTION' FROM promo where anneegtr='GTR2' and annee=2005 and formation = 'APP';

----- LPRT FI/FC
insert into scolar_events (etudid, event_date, formsemestre_id, event_type)
SELECT etudid, '2005-09-30', 'SEM1272', 'INSCRIPTION' FROM promo where anneegtr='LPRT' and annee=2005 and formation = 'LPRTFC';

---- LP RT FAP
insert into scolar_events (etudid, event_date, formsemestre_id, event_type)
SELECT etudid, '2005-09-29', 'SEM1401', 'INSCRIPTION' FROM promo where anneegtr='LPRTFAP' and annee=2005 and formation = 'LPRTFAP';