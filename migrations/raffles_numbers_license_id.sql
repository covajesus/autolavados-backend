-- Vincula números de rifa con la licencia (cliente SaaS).

ALTER TABLE raffles_numbers
    ADD COLUMN license_id INT NULL AFTER raffle_id,
    ADD KEY idx_raffles_numbers_license_id (license_id);

-- Rellenar desde la rifa padre (opcional, si ya hay datos)
UPDATE raffles_numbers rn
JOIN raffles r ON r.id = rn.raffle_id
SET rn.license_id = r.license_id
WHERE rn.license_id IS NULL AND r.license_id IS NOT NULL;
