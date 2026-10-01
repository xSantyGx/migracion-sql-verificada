CREATE OR ALTER PROCEDURE dbo.outstanding_balance
@policy_id int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT CAST((SELECT ISNULL(SUM(amount),0) FROM dbo.premiums WHERE policy_id=@policy_id)-(SELECT ISNULL(SUM(amount),0) FROM dbo.payments WHERE policy_id=@policy_id) AS decimal(19,4)) AS balance;
END;
