-- Populate the trees table from the latest_modules by utilizing
--   the shred_collxml trigger.
WITH latest_idents AS
  (SELECT module_ident AS ident FROM latest_modules)
SELECT shred_collxml(fileid) FROM module_files
  WHERE filename = 'collection.xml'
        AND module_ident IN (SELECT ident FROM latest_idents)
;
