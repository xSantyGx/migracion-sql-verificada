CREATE OR ALTER PROCEDURE dbo.payment_summary
@policy_id int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT COUNT(*) AS payment_count, CAST(ISNULL(SUM(amount),0) AS decimal(19,4)) AS total FROM dbo.payments WHERE policy_id=@policy_id;
END;
