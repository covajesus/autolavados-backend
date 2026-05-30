-- Agrega license_id (cliente SaaS) a todas las tablas de negocio.
-- Tablas: licenses (omitida), users, branch_offices, tickets, statuses, raffles,
--   raffles_numbers, brands, clients, car_types, sliders, services, customers,
--   configurations, rols, branch_offices_washers, branch_offices_managers,
--   expenses, branch_collections, manager_cash_closures,
--   tickets_branch_offices_services, washer_daily_groups,
--   washer_daily_group_members, washer_pay_settlements
--
-- Las siguientes ya tienen migración individual (no ejecutar aquí si ya corrieron):
--   users_license_id.sql, branch_offices_license_id.sql, tickets_license_id.sql,
--   statuses_license_id.sql, raffles_license_id.sql, raffles_numbers_license_id.sql

-- users (ver migrations/users_license_id.sql)
-- ALTER TABLE users
--     ADD COLUMN license_id INT NULL AFTER rol_id,
--     ADD KEY idx_users_license_id (license_id);

-- branch_offices (ver migrations/branch_offices_license_id.sql)
-- ALTER TABLE branch_offices
--     ADD COLUMN license_id INT NULL AFTER branch_office,
--     ADD KEY idx_branch_offices_license_id (license_id);

-- tickets (ver migrations/tickets_license_id.sql)
-- ALTER TABLE tickets
--     ADD COLUMN license_id INT NULL AFTER customer_id,
--     ADD KEY idx_tickets_license_id (license_id);

-- statuses (ver migrations/statuses_license_id.sql)
-- ALTER TABLE statuses
--     ADD COLUMN license_id INT NULL AFTER status,
--     ADD KEY idx_statuses_license_id (license_id);

-- raffles (ver migrations/raffles_license_id.sql)
-- ALTER TABLE raffles
--     ADD COLUMN license_id INT NULL AFTER raffle,
--     ADD KEY idx_raffles_license_id (license_id);

-- raffles_numbers (ver migrations/raffles_numbers_license_id.sql)
-- ALTER TABLE raffles_numbers
--     ADD COLUMN license_id INT NULL AFTER raffle_id,
--     ADD KEY idx_raffles_numbers_license_id (license_id);

ALTER TABLE brands
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_brands_license_id (license_id);

ALTER TABLE clients
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_clients_license_id (license_id);

ALTER TABLE car_types
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_car_types_license_id (license_id);

ALTER TABLE sliders
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_sliders_license_id (license_id);

ALTER TABLE services
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_services_license_id (license_id);

ALTER TABLE customers
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_customers_license_id (license_id);

ALTER TABLE configurations
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_configurations_license_id (license_id);

ALTER TABLE rols
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_rols_license_id (license_id);

ALTER TABLE branch_offices_washers
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_branch_offices_washers_license_id (license_id);

ALTER TABLE branch_offices_managers
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_branch_offices_managers_license_id (license_id);

ALTER TABLE expenses
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_expenses_license_id (license_id);

ALTER TABLE branch_collections
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_branch_collections_license_id (license_id);

ALTER TABLE manager_cash_closures
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_manager_cash_closures_license_id (license_id);

ALTER TABLE tickets_branch_offices_services
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_tickets_branch_offices_services_license_id (license_id);

ALTER TABLE washer_daily_groups
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_washer_daily_groups_license_id (license_id);

ALTER TABLE washer_daily_group_members
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_washer_daily_group_members_license_id (license_id);

ALTER TABLE washer_pay_settlements
    ADD COLUMN license_id INT NULL AFTER id,
    ADD KEY idx_washer_pay_settlements_license_id (license_id);
