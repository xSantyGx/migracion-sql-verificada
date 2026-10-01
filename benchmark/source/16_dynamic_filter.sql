CREATE OR ALTER PROCEDURE dbo.dynamic_filter
@status nvarchar(100)
AS
BEGIN
 SET NOCOUNT ON;
 DECLARE @sql nvarchar(max)=N'SELECT id,code FROM dbo.policies WHERE status=@s ORDER BY id'; EXEC sp_executesql @sql,N'@s nvarchar(100)',@s=@status;
END;
