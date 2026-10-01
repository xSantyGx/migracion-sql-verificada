CREATE OR ALTER PROCEDURE dbo.temp_balances
@client_id int
AS
BEGIN
 SET NOCOUNT ON;
 CREATE TABLE #balances(id int,balance decimal(19,4)); INSERT INTO #balances SELECT p.id,ISNULL((SELECT SUM(amount) FROM dbo.premiums WHERE policy_id=p.id),0)-ISNULL((SELECT SUM(amount) FROM dbo.payments WHERE policy_id=p.id),0) FROM dbo.policies p WHERE p.client_id=@client_id; SELECT id,balance FROM #balances ORDER BY id; DROP TABLE #balances;
END;
