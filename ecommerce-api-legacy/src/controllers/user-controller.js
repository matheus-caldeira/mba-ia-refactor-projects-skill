'use strict';

/** Controller de usuários. Apenas orquestra. */
class UserController {
  constructor({ userService }) {
    this._userService = userService;
  }

  async remove(userId) {
    return this._userService.deleteUser(userId);
  }
}

module.exports = { UserController };
