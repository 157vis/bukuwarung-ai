-- Set harga & stok kopi untuk trial client (contoh Logistik AI: jual 35000 → -10 unit)
UPDATE products p
SET price = 3500, stock = 50
FROM auth.users u
WHERE p.user_id::text = u.id::text
  AND lower(u.email) = lower('rafiharliansyah34@gmail.com')
  AND lower(p.name) = 'kopi';

SELECT p.name, p.price, p.stock
FROM products p
JOIN auth.users u ON u.id::text = p.user_id::text
WHERE lower(u.email) = lower('rafiharliansyah34@gmail.com')
  AND lower(p.name) = 'kopi';
