CREATE OR ALTER PROCEDURE dbo.null_and_concat
@policy_id int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT CONCAT(code,':',notes) AS label,ISNULL(notes,N'(sin nota)') AS notes FROM dbo.policies WHERE id=@policy_id;
END;
