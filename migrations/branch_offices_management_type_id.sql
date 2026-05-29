-- Tipo de gestión: 1 = Administrada, 2 = Subarriendo

ALTER TABLE branch_offices
  ADD COLUMN management_type_id INT NULL DEFAULT 1 AFTER branch_office;

UPDATE branch_offices
  SET management_type_id = 1
  WHERE management_type_id IS NULL;

ALTER TABLE branch_offices
  MODIFY COLUMN management_type_id INT NOT NULL DEFAULT 1;
