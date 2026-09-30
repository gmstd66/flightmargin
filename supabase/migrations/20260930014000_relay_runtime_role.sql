-- Least-privilege login role used by the hosted relay-v1 Edge Function.
-- The role password is an operational secret and is intentionally not part
-- of the source-controlled schema.

begin;

do $$
begin
    if not exists (
        select 1 from pg_roles where rolname = 'flightmargin_relay'
    ) then
        create role flightmargin_relay;
    end if;
end
$$;

alter role flightmargin_relay with
    login
    nosuperuser
    nocreatedb
    nocreaterole
    noreplication
    nobypassrls
    noinherit;

revoke all privileges on schema public from flightmargin_relay;
grant usage on schema public to flightmargin_relay;

revoke all privileges on table public.relay_hosts
    from flightmargin_relay;
revoke all privileges on table public.relay_host_credentials
    from flightmargin_relay;
revoke all privileges on table public.relay_devices
    from flightmargin_relay;
revoke all privileges on table public.relay_device_credentials
    from flightmargin_relay;
revoke all privileges on table public.relay_pairing_sessions
    from flightmargin_relay;
revoke all privileges on table public.relay_quota_state
    from flightmargin_relay;
revoke all privileges on table public.relay_rate_limit_buckets
    from flightmargin_relay;

grant select, insert, update on table public.relay_hosts
    to flightmargin_relay;
grant select, insert, update on table public.relay_host_credentials
    to flightmargin_relay;
grant select, insert, update on table public.relay_devices
    to flightmargin_relay;
grant select, insert, update on table public.relay_device_credentials
    to flightmargin_relay;
grant select, insert, update on table public.relay_pairing_sessions
    to flightmargin_relay;
grant select, insert, update on table public.relay_quota_state
    to flightmargin_relay;
grant select, insert, update, delete
    on table public.relay_rate_limit_buckets
    to flightmargin_relay;

drop policy if exists relay_runtime_select on public.relay_hosts;
drop policy if exists relay_runtime_insert on public.relay_hosts;
drop policy if exists relay_runtime_update on public.relay_hosts;
create policy relay_runtime_select on public.relay_hosts
    for select to flightmargin_relay using (true);
create policy relay_runtime_insert on public.relay_hosts
    for insert to flightmargin_relay with check (true);
create policy relay_runtime_update on public.relay_hosts
    for update to flightmargin_relay using (true) with check (true);

drop policy if exists relay_runtime_select on public.relay_host_credentials;
drop policy if exists relay_runtime_insert on public.relay_host_credentials;
drop policy if exists relay_runtime_update on public.relay_host_credentials;
create policy relay_runtime_select on public.relay_host_credentials
    for select to flightmargin_relay using (true);
create policy relay_runtime_insert on public.relay_host_credentials
    for insert to flightmargin_relay with check (true);
create policy relay_runtime_update on public.relay_host_credentials
    for update to flightmargin_relay using (true) with check (true);

drop policy if exists relay_runtime_select on public.relay_devices;
drop policy if exists relay_runtime_insert on public.relay_devices;
drop policy if exists relay_runtime_update on public.relay_devices;
create policy relay_runtime_select on public.relay_devices
    for select to flightmargin_relay using (true);
create policy relay_runtime_insert on public.relay_devices
    for insert to flightmargin_relay with check (true);
create policy relay_runtime_update on public.relay_devices
    for update to flightmargin_relay using (true) with check (true);

drop policy if exists relay_runtime_select on public.relay_device_credentials;
drop policy if exists relay_runtime_insert on public.relay_device_credentials;
drop policy if exists relay_runtime_update on public.relay_device_credentials;
create policy relay_runtime_select on public.relay_device_credentials
    for select to flightmargin_relay using (true);
create policy relay_runtime_insert on public.relay_device_credentials
    for insert to flightmargin_relay with check (true);
create policy relay_runtime_update on public.relay_device_credentials
    for update to flightmargin_relay using (true) with check (true);

drop policy if exists relay_runtime_select on public.relay_pairing_sessions;
drop policy if exists relay_runtime_insert on public.relay_pairing_sessions;
drop policy if exists relay_runtime_update on public.relay_pairing_sessions;
create policy relay_runtime_select on public.relay_pairing_sessions
    for select to flightmargin_relay using (true);
create policy relay_runtime_insert on public.relay_pairing_sessions
    for insert to flightmargin_relay with check (true);
create policy relay_runtime_update on public.relay_pairing_sessions
    for update to flightmargin_relay using (true) with check (true);

drop policy if exists relay_runtime_select on public.relay_quota_state;
drop policy if exists relay_runtime_insert on public.relay_quota_state;
drop policy if exists relay_runtime_update on public.relay_quota_state;
create policy relay_runtime_select on public.relay_quota_state
    for select to flightmargin_relay using (true);
create policy relay_runtime_insert on public.relay_quota_state
    for insert to flightmargin_relay with check (true);
create policy relay_runtime_update on public.relay_quota_state
    for update to flightmargin_relay using (true) with check (true);

drop policy if exists relay_runtime_select
    on public.relay_rate_limit_buckets;
drop policy if exists relay_runtime_insert
    on public.relay_rate_limit_buckets;
drop policy if exists relay_runtime_update
    on public.relay_rate_limit_buckets;
drop policy if exists relay_runtime_delete
    on public.relay_rate_limit_buckets;
create policy relay_runtime_select on public.relay_rate_limit_buckets
    for select to flightmargin_relay using (true);
create policy relay_runtime_insert on public.relay_rate_limit_buckets
    for insert to flightmargin_relay with check (true);
create policy relay_runtime_update on public.relay_rate_limit_buckets
    for update to flightmargin_relay using (true) with check (true);
create policy relay_runtime_delete on public.relay_rate_limit_buckets
    for delete to flightmargin_relay using (true);

commit;
