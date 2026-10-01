CREATE OR ALTER PROCEDURE dbo.client_policies
@client_id int
AS
BEGIN
 SET NOCOUNT ON;
 SELECT id,code,status FROM dbo.policies WHERE @client_id IS NULL OR client_id=@client_id ORDER BY id;
END;
