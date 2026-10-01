CREATE OR ALTER PROCEDURE dbo.top_policies
@limit_count int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT TOP (@limit_count) id,annual_premium FROM dbo.policies WHERE annual_premium IS NOT NULL ORDER BY annual_premium DESC,id;
END;
