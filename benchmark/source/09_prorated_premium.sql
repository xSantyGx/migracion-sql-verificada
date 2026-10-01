CREATE OR ALTER PROCEDURE dbo.prorated_premium
@policy_id int, @days int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT CAST(ROUND(annual_premium * CAST(@days AS decimal(19,4)) / 365,2) AS decimal(19,2)) AS premium FROM dbo.policies WHERE id=@policy_id;
END;
