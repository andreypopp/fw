begin;

create schema fw;

create table fw.f (
  uid         text primary key,
  fid         text
);

create table fw.l (
  lid         text primary key,
  uid         text,
  sid         text,
  ts          timestamp
);

create table fw.s (
  sid         text primary key,
  title       text,
  artist_name text,
  site_name   text,
  tr          text,
  ztid        int
);

create function fw.match_song(songid text)
  returns table(ztid int, surl text, rimgurl text, aimgurl text, title text, artist_name text)
  language plpgsql
as $$
declare
  songdata record;
  ztid int;
begin
  select * into songdata from fw.s where sid = songid;

  if songdata is null then
    return;
  end if;

  if songdata.tr is null then
    songdata.tr = tr = substring(tools.zn2((songdata.artist_name::text[])[1]),1,15)
        ||':'
        ||substring(tools.zn2(songdata.title),1,15);
    update fw.s set tr = songdata.tr where s.sid = songdata.sid;
  end if;

  if songdata.ztid is null then
    select tid into ztid from trb_m trb where trb.tr = songdata.tr limit 1;
    songdata.ztid = ztid;
    update fw.s set ztid = ztid where sid = songdata.sid;
  end if;

  return query (select
    songdata.ztid,
    'http://'||td.stream_url::text||'.zvq.me/'||td.sha::text||'.s' as surl,
    replace(r.image_url, '{size}', '500x500') as rimgurl,
    null as aimgurl,
    songdata.title,
    songdata.artist_name
  from track t
  join tdata td on t.id = td.track_id
  join release r on r.id = t.release_id);
end;
$$;

end;
