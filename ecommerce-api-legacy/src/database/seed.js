'use strict';

/**
 * SO os dados iniciais (P-04).
 *
 * A senha do seed era '123' em texto puro no código original (AP-03). Agora ela e
 * gravada com o mesmo KDF (scrypt) de qualquer senha criada pelo checkout.
 */

/**
 * Senha do usuário de seed. Vem do ambiente; o fallback e apenas para o boot de
 * desenvolvimento e não representa credencial de nenhum ambiente real.
 */
function seedPassword() {
  return process.env.SEED_USER_PASSWORD || 'dev-only-alterar';
}

async function runSeed(db, passwordHasher) {
  const { total } = await db.get('SELECT COUNT(*) AS total FROM users');
  if (total > 0) return; // idempotente: não duplica seed em banco persistente

  const passwordHash = await passwordHasher.hash(seedPassword());

  await db.transaction(async (tx) => {
    await tx.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)', [
      'Leonan',
      'leonan@fullcycle.com.br',
      passwordHash,
    ]);
    await tx.run(
      'INSERT INTO courses (title, price, active) VALUES (?, ?, ?), (?, ?, ?)',
      ['Clean Architecture', 997.0, 1, 'Docker', 497.0, 1]
    );
    await tx.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [1, 1]);
    await tx.run(
      'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
      [1, 997.0, 'PAID']
    );
  });
}

module.exports = { runSeed };
