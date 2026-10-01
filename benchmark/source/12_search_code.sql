CREATE OR ALTER PROCEDURE dbo.search_code
@code nvarchar(100)
AS
BEGIN
 SET NOCOUNT ON;
 SELECT id,code FROM dbo.policies WHERE code COLLATE Latin1_General_100_CI_AS=@code ORDER BY id;
END;
