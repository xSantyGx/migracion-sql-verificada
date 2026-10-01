CREATE OR ALTER PROCEDURE dbo.premium_total
@policy_id int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT CAST(ISNULL(SUM(amount),0) AS decimal(19,4)) AS total FROM dbo.premiums WHERE policy_id=@policy_id;
END;
