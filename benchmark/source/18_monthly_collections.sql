CREATE OR ALTER PROCEDURE dbo.monthly_collections
@month_date date
AS
BEGIN
 SET NOCOUNT ON;
 SELECT EOMONTH(@month_date) AS month_end,CAST(ISNULL(SUM(amount),0) AS decimal(19,4)) AS total FROM dbo.payments WHERE paid_date>=DATEFROMPARTS(YEAR(@month_date),MONTH(@month_date),1) AND paid_date<=EOMONTH(@month_date);
END;
