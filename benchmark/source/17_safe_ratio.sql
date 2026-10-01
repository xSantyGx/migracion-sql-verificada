CREATE OR ALTER PROCEDURE dbo.safe_ratio
@numerator decimal(19,4), @denominator decimal(19,4)
AS
BEGIN
 SET NOCOUNT ON;
 BEGIN TRY SELECT CAST(@numerator/@denominator AS decimal(19,4)) AS ratio,CAST(NULL AS nvarchar(30)) AS error_code; END TRY BEGIN CATCH SELECT CAST(NULL AS decimal(19,4)) AS ratio,N'DIVISION_BY_ZERO' AS error_code; END CATCH;
END;
